"""
MCP Client for Google Gemini AI integration

Note: This client requires the GEMINI_API_KEY environment variable to be set at runtime.
No keys or secrets are stored in this repository.
"""

import asyncio
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
import os
import time
import logging
import sys
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)


class TokenTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_calls = 0
        self.token_log = []

        self.last_call_tokens = {"input": 0, "output": 0, "total": 0, "cost": 0}

        self.input_cost_per_1k = 0.0000015
        self.output_cost_per_1k = 0.0025

    def add_usage(
        self, input_tokens: int, output_tokens: int, description: str = "API call"
    ):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.api_calls += 1

        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        total_cost = input_cost + output_cost

        self.last_call_tokens = {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
            "cost": total_cost,
            "description": description,
        }

        usage_entry = {
            "timestamp": time.time(),
            "description": description,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": total_cost,
        }
        self.token_log.append(usage_entry)

    def get_last_call_usage(self):
        return self.last_call_tokens

    def get_summary(self):
        total_tokens = self.total_input_tokens + self.total_output_tokens
        total_cost = (self.total_input_tokens / 1000) * self.input_cost_per_1k + (
            self.total_output_tokens / 1000
        ) * self.output_cost_per_1k

        return {
            "api_calls": self.api_calls,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": total_cost,
            "last_call": self.last_call_tokens,
            "token_history": (
                self.token_log[-10:] if len(self.token_log) > 10 else self.token_log
            ),
        }

    def print_summary(self):
        summary = self.get_summary()

        print("\n" + "=" * 50)
        print(" TOKEN USAGE SUMMARY ")
        print("=" * 50)
        print(f"Total API calls: {summary['api_calls']}")
        print(f"Input tokens: {summary['input_tokens']:,}")
        print(f"Output tokens: {summary['output_tokens']:,}")
        print(f"Total tokens: {summary['total_tokens']:,}")
        print(f"Estimated cost: ${summary['estimated_cost']:.4f}")
        print("=" * 50)

    def reset(self):
        """Reset the token tracker"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_calls = 0
        self.token_log = []
        self.last_call_tokens = {"input": 0, "output": 0, "total": 0, "cost": 0}

    def extract_token_usage(self, response):
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata"):
            if hasattr(response.usage_metadata, "prompt_token_count"):
                input_tokens = response.usage_metadata.prompt_token_count
            if hasattr(response.usage_metadata, "candidates_token_count"):
                output_tokens = response.usage_metadata.candidates_token_count

        if input_tokens == 0 and output_tokens == 0:

            prompt_text = str(getattr(response, "prompt", ""))
            input_tokens = len(prompt_text.split()) * 1.3

            output_text = ""
            if hasattr(response, "candidates"):
                for candidate in response.candidates:
                    if hasattr(candidate, "content") and hasattr(
                        candidate.content, "parts"
                    ):
                        for part in candidate.content.parts:
                            if hasattr(part, "text"):
                                output_text += part.text

            output_tokens = len(output_text.split()) * 1.3

        return int(input_tokens), int(output_tokens)


class McpState:
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    ERROR = "error"
    CLOSED = "closed"


class MCPClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")

        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

        self.client = genai.Client()

        self.model_name = "gemini-2.5-flash"
        self.model_final = "gemini-2.5-flash"
        self.fallback_model = "gemini-1.5-flash"

        self.conversation_history = []
        self.token_tracker = TokenTracker()
        self.mcp_state = McpState.DISCONNECTED
        self.last_error = None
        self.tools_cache = []
        self.server_path = None
        self.connected_at = None
        self.debug_mode = False
        self.system_prompt = None
        self.request_queue = asyncio.Queue()
        self.response_map = {}
        self.request_lock = asyncio.Lock()
        self.worker_task = None
        self.next_request_id = 0
        self.query_counter = 0
        self.document_counter = 0
        self.operation_metrics = {
            "queries_executed": 0,
            "documents_processed": 0,
            "folders_scanned": 0,
        }

    def create_optimized_system_prompt(self):
        server_type = "unknown"
        if hasattr(self, "server_path"):
            if "samsara" in self.server_path.lower():
                server_type = "samsara"
            elif "rfx_raw" in self.server_path.lower():
                server_type = "rfx_raw"
            elif "rfx" in self.server_path.lower():
                server_type = "rfx"

        base_prompt = """
        You are an expert-level AI assistant specializing in data analysis and strategic insight generation using MCP tools. Your primary goal is to produce highly detailed, comprehensive, and exceptionally well-written reports based on user requests.
        **CORE OBJECTIVES:**
        1.  **Depth & Comprehensiveness:** Go beyond surface-level answers. Provide thorough analysis, exploring nuances, implications, and relevant context. Synthesize information from multiple tool calls if necessary to build a complete picture. Aim for substantial, informative responses.
        2.  **Clarity & Structure:** Present findings in a highly organized, professional format. Use clear organization with headings, sections, and bullet points when appropriate. Ensure a logical flow from overview to specific details and insights.
        3.  **Insight Generation:** Do not just present raw data. Extract meaningful insights, identify trends, anomalies, potential causes, and strategic implications. Generate executive summaries that capture the essence of the findings.
        4.  **Table Generation Where Applicable:** Generate markdown tables if you think it will help clearly present your findings.
        5.  **Professional Tone:** Maintain a formal, objective, and authoritative tone. Write clearly, concisely (within the context of being comprehensive), and use precise language.
        """

        server_contexts = {
            "samsara": """
        **CONTEXT - COMPETITIVE INTELLIGENCE:**
        You are analyzing competitive intelligence data about Samara, a key competitor. The documents in the connected folders contain vital competitive intelligence information. When analyzing this data:
        - Focus on understanding Samara's market positioning, strategies, and capabilities
        - Look for patterns in their product offerings, pricing, and market approach
        - Identify potential competitive advantages or weaknesses
        - Pay attention to temporal trends and strategic shifts
        - Consider implications for market competition and strategic response
        """,
            "rfx": """
        **CONTEXT - SALES PIPELINE ANALYSIS:**
        You are analyzing data from our sales pipeline. The data represents our sales activities and opportunities. When analyzing this data:
        - Look for patterns in sales performance and pipeline health
        - Identify trends in win rates, deal sizes, and sales cycles
        - Analyze the effectiveness of different sales strategies
        - Track key metrics and their changes over time
        - Focus on actionable insights that could improve sales outcomes
        """,
            "rfx_raw": """
        **CONTEXT - CUSTOMER INTERACTION ANALYSIS:**
        You are analyzing raw data from individual sales calls and customer interactions. The documents contain detailed notes from prospective customers interested in our services. When analyzing this data:
        - Look for common themes and patterns across customer interactions
        - Identify frequently mentioned needs, concerns, or requirements
        - Analyze customer sentiment and engagement levels
        - Pay attention to specific use cases or requirements mentioned
        - Synthesize individual interactions into broader insights about customer needs
        """,
        }

        guidelines = """
        **TOOL USAGE PROTOCOL:**
        - Autonomously determine and utilize the necessary MCP tools to gather all required data for a thorough analysis in response to the user's query.
        - Execute tool calls efficiently. Avoid unnecessary steps or narration about tool selection or execution.
        - If multiple data points or sources are needed, use tools comprehensively to acquire them before generating the final analysis.

        **ANALYSIS & REPORTING GUIDELINES:**
        - **No Meta-Commentary:** Directly present the analysis and findings. Do *not* describe your internal thought process, planning stages, or intentions (e.g., avoid phrases like "I will now analyze...", "First, I need to...", "Looking at the data...").
        - **Structure:**
            - Start with a concise **Executive Summary** (unless inappropriate for the query length).
            - Use clean markdown headings and sections
            - Use clean markdown bullet points
            - Use markdown for lists, tables, and other structured content.
            - Ensure logical progression and coherence throughout the report.
        - **Content:**
            - Include specific data points, metrics, and evidence gathered from the tools.
            - Elaborate on findings; explain *why* something might be significant.
            - Provide context where necessary for understanding.
            - Aim for exhaustive coverage of the user's request.

        **IMPORTANT - NO CODE BLOCKS, BUT ALWAYS USE CLEAN MARKDOWN:**
        - Never use code blocks (```).

        **FINAL IMPERATIVE:** Your output must be significantly detailed, demonstrably comprehensive, professionally structured, and insightful. Assume the user requires a deep-dive analysis suitable for strategic decision-making. We need facts, not recommendations.
        """

        full_prompt = base_prompt
        if server_type in server_contexts:
            full_prompt += "\n" + server_contexts[server_type]
        full_prompt += "\n" + guidelines

        return full_prompt

    def _convert_to_gemini_format(self, messages):
        gemini_messages = []
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            if role == "user":
                if isinstance(content, str):
                    gemini_messages.append(content)
                elif isinstance(content, list):
                    text_parts = []
                    for item in content:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif item.get("type") == "tool_result":
                                tool_name = item.get("tool_name", "unknown tool")
                                tool_content = item.get("content", [])
                                result_parts = []
                                for content_item in tool_content:
                                    if (
                                        isinstance(content_item, dict)
                                        and content_item.get("type") == "text"
                                    ):
                                        result_parts.append(
                                            content_item.get("text", "")
                                        )

                                if result_parts:
                                    formatted_result = (
                                        f"Tool result from {tool_name}:\n"
                                        + "\n".join(result_parts)
                                    )
                                    text_parts.append(formatted_result)

                    if text_parts:
                        gemini_messages.append("\n\n".join(text_parts))
            elif role == "assistant":
                if isinstance(content, str):
                    gemini_messages.append(f"Previous assistant response: {content}")

        if len(gemini_messages) > 1:
            return "\n\n---\n\n".join(gemini_messages)
        elif gemini_messages:
            return gemini_messages[0]
        else:
            return ""

    async def connect_to_server(self, server_script_path: str):
        self.server_path = server_script_path
        self.mcp_state = McpState.CONNECTING

        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            self.mcp_state = McpState.ERROR
            self.last_error = "Server script must be a .py or .js file"
            raise ValueError(self.last_error)

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        self.mcp_state = McpState.CONNECTED

        try:
            await self.session.initialize()
            self.mcp_state = McpState.INITIALIZED
            self.connected_at = time.time()
        except Exception as e:
            self.mcp_state = McpState.ERROR
            self.last_error = str(e)
            raise

        response = await self.session.list_tools()
        tools = response.tools
        self.tools_cache = tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        self.system_prompt = self.create_optimized_system_prompt()

        self.worker_task = asyncio.create_task(self._process_queue())

    async def ensure_connection(self):
        if self.session is None:
            logger.warning("No active session, cannot check connection health")
            return False

        try:
            response = await asyncio.wait_for(self.session.list_tools(), timeout=5.0)
            return True
        except Exception as e:
            logger.error("Connection health check failed: %s", str(e))
            return False

    async def reconnect(self):
        if not self.server_path:
            logger.error("No server path available for reconnection")
            raise RuntimeError("No server path available for reconnection")

        logger.info("Attempting to reconnect to server at %s", self.server_path)

        self.exit_stack = AsyncExitStack()
        self.session = None

        await self.connect_to_server(self.server_path)
        logger.info("Successfully reconnected to server")

    async def call_gemini_with_fallback(
        self,
        messages,
        system=None,
        tools=None,
        max_tokens=5000,
        temperature=None,
        model=None,
    ):
        try:
            # Convert messages to Gemini format
            content = self._convert_to_gemini_format(messages)

            # Prepare the prompt
            prompt_parts = []
            if system:
                prompt_parts.append(f"System: {system}")
            prompt_parts.append(f"User: {content}")

            prompt = "\n\n".join(prompt_parts)

            # Prepare tools if provided
            tools_config = None
            if tools and isinstance(tools, list) and len(tools) > 0:
                tools_config = []
                for tool in tools:
                    tool_config = {
                        "function_declarations": [
                            {
                                "name": tool["name"],
                                "description": tool.get("description", ""),
                                "parameters": self._clean_schema_for_gemini(
                                    tool.get("input_schema", {})
                                ),
                            }
                        ]
                    }
                    tools_config.append(tool_config)

            # Prepare generation config
            config = types.GenerateContentConfig(
                temperature=temperature or 0.2,
                max_output_tokens=max_tokens,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0
                ),  # Disable thinking for speed
                tools=tools_config if tools_config else None,
            )

            # Make the API call
            response = self.client.models.generate_content(
                model=self.model_name, contents=prompt, config=config
            )

            # Extract token usage
            if hasattr(response, "usage_metadata"):
                input_tokens = response.usage_metadata.prompt_token_count or 0
                output_tokens = response.usage_metadata.candidates_token_count or 0
            else:
                # Fallback token estimation
                input_tokens = len(prompt.split()) * 1.3
                output_tokens = (
                    len(self.extract_text_from_response(response).split()) * 1.3
                )

            self.token_tracker.add_usage(
                int(input_tokens), int(output_tokens), "Primary API Call"
            )

            return response

        except Exception as primary_error:
            logger.error(f"Primary Gemini API call failed: {str(primary_error)}")
            try:

                # Create fallback config without tools
                fallback_config = types.GenerateContentConfig(
                    temperature=temperature or 0.2,
                    max_output_tokens=max_tokens,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                )

                response = self.client.models.generate_content(
                    model=self.fallback_model, contents=prompt, config=fallback_config
                )

                if hasattr(response, "usage_metadata"):
                    input_tokens = response.usage_metadata.prompt_token_count or 0
                    output_tokens = response.usage_metadata.candidates_token_count or 0
                else:
                    input_tokens = len(prompt.split()) * 1.3
                    output_tokens = (
                        len(self.extract_text_from_response(response).split()) * 1.3
                    )

                self.token_tracker.add_usage(
                    int(input_tokens), int(output_tokens), "Fallback API Call"
                )

                return response

            except Exception as model_fallback_error:
                logger.error(f"Model fallback call failed: {str(model_fallback_error)}")

                if tools:
                    try:

                        # Create config without tools for fallback
                        no_tools_config = types.GenerateContentConfig(
                            temperature=temperature or 0.2,
                            max_output_tokens=max_tokens,
                            thinking_config=types.ThinkingConfig(thinking_budget=0),
                        )

                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=no_tools_config,
                        )

                        if hasattr(response, "usage_metadata"):
                            input_tokens = (
                                response.usage_metadata.prompt_token_count or 0
                            )
                            output_tokens = (
                                response.usage_metadata.candidates_token_count or 0
                            )
                        else:
                            input_tokens = len(prompt.split()) * 1.3
                            output_tokens = (
                                len(self.extract_text_from_response(response).split())
                                * 1.3
                            )

                        self.token_tracker.add_usage(
                            int(input_tokens),
                            int(output_tokens),
                            "Fallback without tools",
                        )

                        response._no_tools_fallback = True
                        return response

                    except Exception as fallback_error:
                        logger.error(
                            f"Fallback without tools failed: {str(fallback_error)}"
                        )

                raise primary_error

    def extract_text_from_response(self, response):
        """Extract text content from a Google GenAI response"""
        if isinstance(response, str):
            return response

        if hasattr(response, "text"):
            return response.text

        # Handle the new Google GenAI response format
        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, "content") and candidate.content:
                    for part in candidate.content.parts:
                        if hasattr(part, "text"):
                            return part.text

        # Fallback for different response formats
        if hasattr(response, "message") and isinstance(response.message, dict):
            return response.message.get("content", "")
        if isinstance(response, dict):
            if "message" in response and isinstance(response["message"], dict):
                return response["message"].get("content", "")

        return str(response)

    def _clean_schema_for_gemini(self, schema):
        # Clean schema for Gemini compatibility
        if not schema or not isinstance(schema, dict):
            return schema

        clean_schema = {}

        for key, value in schema.items():
            if key == "default":
                continue
            elif key == "properties" and isinstance(value, dict):
                clean_properties = {}
                for prop_name, prop_schema in value.items():
                    clean_properties[prop_name] = self._clean_schema_for_gemini(
                        prop_schema
                    )
                clean_schema["properties"] = clean_properties
            elif key == "items" and isinstance(value, dict):
                clean_schema["items"] = self._clean_schema_for_gemini(value)
            elif isinstance(value, dict):
                clean_schema[key] = self._clean_schema_for_gemini(value)
            else:
                clean_schema[key] = value

        if "properties" in clean_schema and "type" not in clean_schema:
            clean_schema["type"] = "object"

        if clean_schema.get("type") == "array" and "items" in clean_schema:
            if (
                isinstance(clean_schema["items"], dict)
                and "type" not in clean_schema["items"]
            ):
                if "properties" in clean_schema["items"]:
                    clean_schema["items"]["type"] = "object"
                else:
                    clean_schema["items"]["type"] = "string"

        if "query_results" in clean_schema.get("properties", {}):
            if "type" not in clean_schema["properties"]["query_results"]:
                clean_schema["properties"]["query_results"]["type"] = "string"
        return clean_schema

    async def process_tool_calls(self, response):
        results = []
        pending_requests = []

        if hasattr(response, "_no_tools_fallback") and response._no_tools_fallback:

            return results

        if not hasattr(response, "candidates") or not response.candidates:
            logger.warning("No candidates in response, skipping tool call processing")
            return results

        function_calls = []

        try:
            for candidate in response.candidates:
                if (
                    hasattr(candidate, "content")
                    and candidate.content
                    and hasattr(candidate.content, "parts")
                ):
                    for part in candidate.content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            function_calls.append(part.function_call)

            if not function_calls:

                return results

            async with self.request_lock:
                for function_call in function_calls:
                    if not hasattr(function_call, "name") or not function_call.name:
                        logger.warning("Function call without name, skipping")
                        continue

                    tool_name = function_call.name
                    tool_args = {}
                    if hasattr(function_call, "args"):
                        if isinstance(function_call.args, dict):
                            tool_args = function_call.args
                        elif hasattr(function_call.args, "to_dict"):
                            tool_args = function_call.args.to_dict()
                        else:
                            logger.warning(
                                f"Unexpected args format: {type(function_call.args)}"
                            )

                    request_id = f"{self.next_request_id}"
                    self.next_request_id += 1

                    await self.request_queue.put((request_id, tool_name, tool_args))

                    pending_requests.append(
                        {
                            "request_id": request_id,
                            "tool_name": tool_name,
                            "tool_args": tool_args,
                            "tool_use_id": str(id(function_call)),
                        }
                    )

            for req in pending_requests:
                request_id = req["request_id"]
                retry_count = 0
                max_retries = 10
                backoff_time = 0.1

                while request_id not in self.response_map and retry_count < max_retries:
                    await asyncio.sleep(backoff_time)
                    backoff_time *= 1.5
                    retry_count += 1

                if request_id in self.response_map:
                    response = self.response_map.pop(request_id)

                    if response["success"]:
                        result_content = []
                        if (
                            hasattr(response["result"], "content")
                            and response["result"].content
                        ):
                            for item in response["result"].content:
                                if hasattr(item, "type") and hasattr(item, "text"):
                                    result_content.append(
                                        {"type": item.type, "text": item.text}
                                    )

                        results.append(
                            {
                                "tool": req["tool_name"],
                                "args": req["tool_args"],
                                "result": response["result"],
                                "success": True,
                                "tool_use_id": req["tool_use_id"],
                                "content": result_content,
                                "metadata": {
                                    "result_type": "success",
                                    "size": (
                                        len(str(response["result"].content))
                                        if hasattr(response["result"], "content")
                                        else 0
                                    ),
                                },
                            }
                        )
                    else:
                        results.append(
                            {
                                "tool": req["tool_name"],
                                "args": req["tool_args"],
                                "error": response["error"],
                                "success": False,
                                "tool_use_id": req["tool_use_id"],
                                "metadata": {
                                    "result_type": "error",
                                    "error_class": "Exception",
                                },
                            }
                        )
                else:
                    results.append(
                        {
                            "tool": req["tool_name"],
                            "args": req["tool_args"],
                            "error": "Request timed out",
                            "success": False,
                            "tool_use_id": req["tool_use_id"],
                            "metadata": {"result_type": "timeout"},
                        }
                    )

            for result in results:
                tool_name = result.get("tool", "")
                if tool_name:
                    if "query" in tool_name.lower() or "search" in tool_name.lower():
                        self.operation_metrics["queries_executed"] += 1

                    elif tool_name == "search_drive_files" and result.get("success"):
                        try:
                            content = result.get("result").content
                            file_count = 0
                            for item in content:
                                if hasattr(item, "text"):
                                    file_count += item.text.count('{"mimeType":')

                            if file_count > 0:
                                self.operation_metrics[
                                    "documents_processed"
                                ] += file_count
                            else:

                                self.operation_metrics["documents_processed"] += 1
                        except:
                            self.operation_metrics["documents_processed"] += 1

                    elif "file" in tool_name.lower() or "document" in tool_name.lower():
                        self.operation_metrics["documents_processed"] += 1

                    elif tool_name == "list_tables" and result.get("success"):
                        try:
                            content = result.get("result").content
                            table_count = 0
                            for item in content:
                                if hasattr(item, "text"):
                                    table_count += len(item.text.strip().split("\n"))

                            if table_count > 0:
                                self.operation_metrics["folders_scanned"] += table_count
                            else:
                                self.operation_metrics["folders_scanned"] += 1
                        except:
                            self.operation_metrics["folders_scanned"] += 1
                    elif "folder" in tool_name.lower() or "list" in tool_name.lower():
                        self.operation_metrics["folders_scanned"] += 1

        except Exception as e:
            logger.error(f"Error processing function calls: {str(e)}", exc_info=True)

        self._report_progress(
            "Updated operation metrics", {"metrics": self.operation_metrics}
        )

        return results

    def _format_tool_results_for_gemini(self, results):
        formatted_results = []

        for result in results:
            if result["success"]:
                content = result["result"].content
                formatted_content = ""

                for item in content:
                    if hasattr(item, "type") and item.type == "text":
                        formatted_content += item.text + "\n"

                formatted_results.append(
                    f"Result from tool '{result['tool']}':\n{formatted_content}"
                )
            else:
                formatted_results.append(
                    f"Error from tool '{result['tool']}': {result['error']}"
                )

        return "\n\n".join(formatted_results)

    async def process_query(self, query: str) -> str:
        self.conversation_history.append({"role": "user", "content": query})

        await self.manage_context()

        response = await self.session.list_tools()

        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        print("\nAnalyzing your request...")

        classification_prompt = f"""
        You are classifying the type of query. For this response ONLY:
        - If the user's message is casual conversation (like "how are you?", greetings, etc.), respond with "CASUAL_CONVERSATION"
        - If the user is asking for help or information about this system, respond with "HELP_REQUEST"
        - If the user is asking for information that requires data access or analysis, respond with "ANALYSIS_NEEDED"
        
        Respond with just one of these classifications and nothing else.
        
        User query: {query}
        """

        initial_response = await self.call_gemini_with_fallback(
            messages=[{"role": "user", "content": classification_prompt}], max_tokens=50
        )

        classification = (
            self.extract_text_from_response(initial_response).strip().upper()
        )

        if "CASUAL_CONVERSATION" in classification:
            return await self._handle_casual_conversation(query)
        elif "HELP_REQUEST" in classification:
            return await self._handle_help_request(query)
        else:
            print("\n📊 Starting strategic analysis process...")
            return await self.strategic_analysis(query)

    async def _handle_casual_conversation(self, query: str) -> str:
        print("\n💬 Casual conversation detected - responding directly...")
        response = await self.call_gemini_with_fallback(
            messages=self.conversation_history, max_tokens=300, temperature=0.85
        )
        reply = self.extract_text_from_response(response)
        self.conversation_history.append({"role": "assistant", "content": reply})

        return reply

    async def _handle_help_request(self, query: str) -> str:
        print("\n📚 Help request detected - providing system information...")

        help_prompt = f"""
        You are explaining how this MCP client works. Your explanation should:
        - Describe the system's capabilities in simple terms
        - Explain how users can interact with data and documents
        - Suggest sample queries the user might try
        - Be helpful and concise
        
        User question: {query}
        """

        response = await self.call_gemini_with_fallback(
            messages=[{"role": "user", "content": help_prompt}],
            max_tokens=800,
            temperature=0.3,
        )

        reply = self.extract_text_from_response(response)

        self.conversation_history.append({"role": "assistant", "content": reply})

        return reply

    async def strategic_analysis(self, query: str) -> str:
        print("\n" + "=" * 80)
        print(" STARTING STRATEGIC ANALYSIS ".center(80, "="))
        print(f" Query: {query} ".center(80, "="))
        print("=" * 80 + "\n")

        self._report_progress("Analyzing your request...")

        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        tool_descriptions = "\n".join(
            [
                f"- {tool['name']}: {tool['description'] or 'No description'}"
                for tool in available_tools
            ]
        )

        print("\n" + "=" * 80)
        print(" PHASE 1: QUESTION ANALYSIS ".center(80, "="))
        print("=" * 80)

        self._report_progress(
            """IMPORTANT FORMATTING INSTRUCTIONS:
                1. Always report progress in this exact format:
                - "Phase 1: Analyzing query requirements..."
                - "Phase 2: Developing analysis strategy..."
                - "Phase 3: Executing analysis plan..."
                - "Phase 4: Critically evaluating findings..."
                - "Phase 5: Synthesizing comprehensive analysis..."
                2. When executing steps, always use: "Executing Step X/Y: [description]"
                """
        )

        analysis_prompt = f"""
        First, analyze this query to understand its full scope and requirements:
        
        "{query}"
        
        Perform a detailed breakdown of:
        1. Core information needs
        2. Potential sub-questions that need answering
        3. Types of data required to provide a comprehensive answer
        4. Metrics or specific details the user likely needs
        
        Your output should identify what a complete answer looks like.
        """

        print("\nSending prompt to model:")
        print(f"{analysis_prompt}\n")

        query_analysis_response = await self.call_gemini_with_fallback(
            messages=[{"role": "user", "content": analysis_prompt}], max_tokens=5000
        )

        query_analysis = self.extract_text_from_response(query_analysis_response)

        print("\n" + "=" * 80)
        print(" PHASE 2: STRATEGIC PLANNING ".center(80, "="))
        print("=" * 80)

        self._report_progress("Phase 2: Developing analysis strategy...")

        planning_prompt = f"""
            You are developing a strategic plan to answer the user's query.

            Query: "{query}"

            Query Analysis: 
            {query_analysis}

            Your task is to:
            1. Analyze what information is needed to fully answer the query
            2. Determine which specific tools should be used in which order
            3. Create a detailed step-by-step plan with 4-6 steps (appropriate to query complexity)

            IMPORTANT FORMATTING: Follow these exact formatting conventions for consistent progress tracking:
            1. Start your response with "## Analysis Strategy" followed by 2-3 sentences
            2. Then include "## Step-by-Step Plan" with numbered steps
            3. Each step should be a descriptive explanation that includes the tool name naturally in the text
            4. Do NOT use bold or backticks formatting for tools

            IMPORTANT: You must ONLY use tools that are actually available. Here are the tools you can use:

            {tool_descriptions}

            DO NOT reference tools that are not in this list. DO NOT make up tools that don't exist.
            DO NOT execute any tools yet. Just create a detailed plan.

            FORMAT YOUR RESPONSE AS:

            ## Analysis Strategy
            [1-6 sentences explaining your overall approach]

            ## Step-by-Step Plan
            1. Use the [tool_name] to [descriptive explanation of what this step will do]
            - **Parameters:** `parameter1="value1"`, `parameter2="value2"`
            - **Information Obtained:** [what this step will retrieve]
            - **Contribution:** [how this contributes to the answer]
            ...

            REMEMBER:
            - While we are looking for an efficient plan, when analyzing resources like databases or files, capture the full scope of the data.
            - Be thorough but efficient in your plan
            - Only reference tools that actually exist in the list above
            - Be specific about which tool to use in each step and what parameters to pass
            """

        print("\nSending planning prompt to model:")
        print(f"{planning_prompt}\n")

        planning_response = await self.call_gemini_with_fallback(
            messages=[{"role": "user", "content": planning_prompt}], max_tokens=5000
        )

        strategy_text = self.extract_text_from_response(planning_response)

        steps = self._parse_strategy_steps(strategy_text)
        total_steps = len(steps)

        formatted_plan = f"""## Analysis Strategy and Step-by-Step Plan
        {strategy_text}
        """
        self._report_progress(formatted_plan)

        execution_context = f"""
        Original query: "{query}"
        
        Query analysis:
        {query_analysis}
        
        Strategic plan:
        {strategy_text}
        """

        print("\n" + "=" * 80)
        print(" PHASE 3: EXECUTING ANALYSIS PLAN ".center(80, "="))
        print("=" * 80)

        self._report_progress(
            "Phase 3: Executing analysis plan with progressive insight development..."
        )

        intermediate_insights = []

        for i, step in enumerate(steps):
            print("\n" + "-" * 80)
            print(f" STEP {i+1}/{total_steps}: {step['description']} ".center(80, "-"))
            print("-" * 80)

            cleaned_description = step["description"]
            step_message = f"Executing Step {i+1}/{total_steps}: {cleaned_description}"

            self._report_progress(
                step_message,
                {"step": i + 1, "total": total_steps, "status": "in-progress"},
            )

            execution_prompt = f"""
            {execution_context}
            
            Now, execute ONLY this step: {step['description']}
            
            Available tools:
            {tool_descriptions}
            
            ONLY use tools from this list. DO NOT provide analysis yet - just execute the tool call needed for this step.
            """

            print("\nSending execution prompt to model:")
            print(f"{execution_prompt}\n")

            execution_response = await self.call_gemini_with_fallback(
                messages=[{"role": "user", "content": execution_prompt}],
                tools=available_tools,
                max_tokens=5000,
            )

            print("\nExecution response:")
            self.extract_text_from_response(execution_response)

            step_results = await self.process_tool_calls(execution_response)

            print("\nTool call results:")
            for result in step_results:
                print(f"Tool: {result['tool']}")
                print(f"Args: {result['args']}")
                if result["success"]:
                    content = (
                        result["result"].content
                        if hasattr(result["result"], "content")
                        else []
                    )
                    content_text = ""
                    for item in content:
                        if hasattr(item, "text"):
                            content_text += item.text
                    print(f"Success: {result['success']}")
                    print(
                        f"Content: {content_text[:500]}..."
                        if len(content_text) > 500
                        else f"Content: {content_text}"
                    )
                else:
                    print(f"Error: {result['error']}")
                print("-" * 40)

            self._report_progress(
                f"Successfully completed step {i+1}",
                {
                    "step": i + 1,
                    "total": total_steps,
                    "status": "completed",
                    "tool": (
                        step_results[0]["tool"]
                        if step_results and len(step_results) > 0
                        else "unknown"
                    ),
                },
            )

            result_text = self._format_tool_results_for_gemini(step_results)

            print("\n" + "-" * 80)
            print(f" INSIGHTS FOR STEP {i+1} ".center(80, "-"))
            print("-" * 80)

            insight_prompt = f"""
            Based on the following information:
            
            Original query: "{query}"
            
            Step {i+1} results: 
            {result_text}
            
            Previous findings:
            {' '.join(intermediate_insights)}
            
            Generate key insights from ONLY the most recent step results. Focus on:
            1. What new information was discovered
            2. How this connects to previous findings (if applicable)
            3. What patterns, anomalies, or important points emerge
            
            Format your response as 3-5 concise but detailed bullet points of key findings.
            """

            print("\nSending insight prompt to model:")
            print(f"{insight_prompt}\n")

            insight_response = await self.call_gemini_with_fallback(
                messages=[{"role": "user", "content": insight_prompt}], max_tokens=5000
            )

            step_insights = self.extract_text_from_response(insight_response)
            intermediate_insights.append(
                f"\n--- INSIGHTS FROM STEP {i+1} ---\n{step_insights}"
            )

            execution_context += f"\n\n--- STEP {i+1} RESULTS ---\n{result_text}\n\n--- STEP {i+1} INSIGHTS ---\n{step_insights}"

            self._report_progress(
                f"Step {i+1}/{total_steps} processed data",
                {
                    "metrics": self.operation_metrics,
                    "step": i + 1,
                    "status": "in-progress",
                },
            )

        print("\n" + "=" * 80)
        print(" PHASE 4: CRITICAL EVALUATION ".center(80, "="))
        print("=" * 80)

        self._report_progress("Phase 4: Critically evaluating findings...")

        evaluation_prompt = f"""
        {execution_context}
        
        Now that all data has been gathered, perform an extensive critical evaluation of the findings:

        1. Identify any gaps, limitations, or uncertainties in the data with detailed explanation
        2. Consider multiple potential alternative interpretations for each major finding
        3. Evaluate the strength and reliability of the evidence in depth
        4. Note any additional information that would strengthen the analysis
        5. Analyze potential biases or limitations in data collection methods
        6. Consider how different stakeholders might interpret these findings
        7. Examine the findings in broader context and historical perspective
        8. Identify connections between different data points that weren't explicitly explored

        Provide a comprehensive, nuanced assessment of the findings before moving to final synthesis.
        """

        print("\nSending evaluation prompt to model:")
        print(f"{evaluation_prompt}\n")

        evaluation_response = await self.call_gemini_with_fallback(
            messages=[{"role": "user", "content": evaluation_prompt}], max_tokens=5000
        )

        evaluation_text = self.extract_text_from_response(evaluation_response)
        execution_context += f"\n\n--- CRITICAL EVALUATION ---\n{evaluation_text}"

        print("\n" + "=" * 80)
        print(" PHASE 5: COMPREHENSIVE SYNTHESIS ".center(80, "="))
        print("=" * 80)

        self._report_progress("Phase 5: Synthesizing comprehensive analysis...")

        synthesis_prompt = f"""
        {execution_context}
        
        Now synthesize all information into a comprehensive, strategic analysis that thoroughly answers the original query:
        
        "{query}"
        
        Your synthesis should:
        
        1. Begin with an executive summary of key findings and insights (2-3 paragraphs) with the total analysis being 10-15 paragraphs
        2. Use clear section headings markdown formatting
        3. Present specific data points and metrics. If tables are applicable, use them.
        5. Provide nuanced analysis coherently ties together findings, but don't mention the tools used to generate the findings including sql queries or table schemas.
        6. Address the original query comprehensively from multiple angles
        7. Present information in logical progression from overview to specific details, again focus on facts found, not tools used. 
        8. Include contextual information necessary for full understanding
        9. Structure information clearly use markdown formatting
        10. End with a concise conclusion that directly addresses the original query
        
        IMPORTANT - FORMATTING INSTRUCTIONS:
        - Do NOT use code blocks with backticks (```)
        - Use markdown headings with # symbols
        - Use markdown bullet points with - or * symbols
        - Use any other markdown formatting
        

        Aim for exceptional depth and comprehensiveness. The reader should gain a complete understanding without needing additional information.
        """

        print("\nSending synthesis prompt to model:")
        print(f"{synthesis_prompt}\n")

        synthesis_response = await self.call_gemini_with_fallback(
            messages=[{"role": "user", "content": synthesis_prompt}],
            max_tokens=100000,
            temperature=0.7,
            model=self.model_final,
        )

        final_analysis = self.extract_text_from_response(synthesis_response)

        self.conversation_history.append(
            {"role": "assistant", "content": final_analysis}
        )

        print("\n" + "=" * 80)
        print(" STRATEGIC ANALYSIS COMPLETE ".center(80, "="))
        print("=" * 80 + "\n")

        return final_analysis

    def _parse_strategy_steps(self, strategy_text: str) -> List[Dict[str, Any]]:
        steps = []
        current_step = None
        in_parameters = False
        in_information = False
        in_contribution = False

        lines = strategy_text.split("\n")

        for line in lines:
            step_match = re.match(r"^\s*(\d+)\.\s+(.*)", line)

            if step_match:
                if current_step:
                    steps.append(current_step)

                number = int(step_match.group(1))
                description = step_match.group(2).strip()
                current_step = {
                    "number": number,
                    "description": description,
                    "parameters": [],
                    "information_obtained": "",
                    "contribution": "",
                }
                in_parameters = False
                in_information = False
                in_contribution = False

            elif not current_step:
                continue

            elif "**Parameters:**" in line or "- Parameters:" in line:
                in_parameters = True
                in_information = False
                in_contribution = False

            elif (
                "**Information Obtained:**" in line or "- Information Obtained:" in line
            ):
                in_parameters = False
                in_information = True
                in_contribution = False

            elif "**Contribution:**" in line or "- Contribution:" in line:
                in_parameters = False
                in_information = False
                in_contribution = True

            elif in_parameters and line.strip():
                param_line = line.strip().replace("`", "").replace("*", "")
                if param_line.startswith("-"):
                    param_line = param_line[1:].strip()
                current_step["parameters"].append(param_line)

            elif in_information and line.strip():
                info_line = line.strip()
                if info_line.startswith("-"):
                    info_line = info_line[1:].strip()
                if current_step["information_obtained"]:
                    current_step["information_obtained"] += " " + info_line
                else:
                    current_step["information_obtained"] = info_line

            elif in_contribution and line.strip():
                contrib_line = line.strip()
                if contrib_line.startswith("-"):
                    contrib_line = contrib_line[1:].strip()
                if current_step["contribution"]:
                    current_step["contribution"] += " " + contrib_line
                else:
                    current_step["contribution"] = contrib_line

        if current_step:
            steps.append(current_step)

        for step in steps:
            tool_match = re.search(r"Use (?:the )?([\w_]+)", step["description"])
            if tool_match:
                step["tool"] = tool_match.group(1)
            else:
                tool_patterns = [
                    r"([\w_]+) tool",
                    r"([\w_]+) function",
                    r"call ([\w_]+)",
                    r"execute ([\w_]+)",
                ]
                for pattern in tool_patterns:
                    match = re.search(pattern, step["description"], re.IGNORECASE)
                    if match:
                        step["tool"] = match.group(1)
                        break

                if "tool" not in step:
                    step["tool"] = None

        return steps

    def _report_progress(self, message, details=None):
        """Report progress through the callback if available"""
        if hasattr(self, "_progress_callback") and callable(self._progress_callback):
            self._progress_callback(message, details)
        else:
            if isinstance(details, dict) and "metrics" in details:
                metrics_str = ", ".join(
                    [f"{k}: {v}" for k, v in details["metrics"].items()]
                )
                print(f"{message} [{metrics_str}]")
            else:
                print(message)

    async def manage_context(self):
        if len(self.conversation_history) <= 10:
            return

        keep_count = 8
        important_context = []

        if self.conversation_history and len(self.conversation_history) > 0:
            important_context.append(self.conversation_history[0])

        tool_call_indices = []
        for i, msg in enumerate(self.conversation_history):
            content = msg.get("content", "")
            if isinstance(content, list) and any(
                item.get("type") == "tool_result"
                for item in content
                if isinstance(item, dict)
            ):
                tool_call_indices.append(i)

        recent_tool_calls = [
            i
            for i in tool_call_indices
            if i >= len(self.conversation_history) - keep_count * 2
        ]

        if recent_tool_calls:
            for idx in recent_tool_calls[-2:]:
                if idx > 0 and idx < len(self.conversation_history):
                    important_context.append(self.conversation_history[idx - 1])
                    important_context.append(self.conversation_history[idx])

        remaining_slots = keep_count - len(important_context)
        if remaining_slots > 0:
            important_context.extend(self.conversation_history[-remaining_slots:])

        seen = set()
        important_context = [
            x for x in important_context if not (x in seen or seen.add(x))
        ]

        self.conversation_history = important_context

    async def cleanup(self):
        if hasattr(self, "worker_task") and self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error cancelling worker task: {str(e)}")

        if hasattr(self, "session") and self.session:
            try:
                if hasattr(self.session, "close"):
                    await self.session.close()
            except Exception as e:
                logger.error(f"Error closing session: {str(e)}")

        if hasattr(self, "exit_stack"):
            try:
                await self.exit_stack.aclose()
            except Exception as e:
                logger.error(f"Error during exit stack cleanup: {str(e)}")
            finally:
                self.exit_stack = AsyncExitStack()
                self.session = None

    async def _process_queue(self):
        while True:
            try:
                request_id, tool_name, tool_args = await self.request_queue.get()

                try:
                    tool_args = self._sanitize_tool_args(tool_name, tool_args)
                    result = await asyncio.wait_for(
                        self.session.call_tool(tool_name, tool_args), timeout=60.0
                    )
                    self.response_map[request_id] = {
                        "success": True,
                        "result": result,
                        "tool": tool_name,
                        "args": tool_args,
                    }

                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    logger.error(error_msg)
                    self.response_map[request_id] = {
                        "success": False,
                        "error": error_msg,
                        "tool": tool_name,
                        "args": tool_args,
                    }

                finally:
                    self.request_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue worker: {str(e)}")
                await asyncio.sleep(1)

    def _sanitize_tool_args(self, tool_name, tool_args):
        # Sanitize tool arguments
        sanitized_args = dict(tool_args)
        if tool_name in [
            "search_drive_files",
            "list_drive_files",
            "list_drive_folders",
        ]:

            if "folder_id" in sanitized_args and sanitized_args["folder_id"] is None:
                sanitized_args["folder_id"] = ""

        if tool_name == "list_drive_folders":
            if (
                "parent_folder_id" in sanitized_args
                and sanitized_args["parent_folder_id"] is None
            ):
                sanitized_args["parent_folder_id"] = ""

        return sanitized_args

    def set_progress_callback(self, callback):
        # Set progress callback for frontend
        self._progress_callback = callback


async def main():
    client = MCPClient()
    try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await client.connect_to_server(sys.argv[1])
                break
            except Exception as e:
                logger.error(
                    "Connection attempt %d failed: %s",
                    attempt + 1,
                    str(e),
                    exc_info=True,
                )
                if attempt == max_retries - 1:
                    print(f"Failed to connect after {max_retries} attempts. Exiting.")
                    sys.exit(1)
                print(
                    f"Connection attempt {attempt+1} failed. Retrying in 2 seconds..."
                )
                await asyncio.sleep(2)

        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
