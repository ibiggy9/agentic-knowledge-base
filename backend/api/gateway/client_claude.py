"""Claude MCP Client (Deprecated - use Gemini client for new development)"""


import asyncio
from typing import Optional, List, Dict, Any, Callable, Union, TypedDict
from contextlib import AsyncExitStack
import json
import re
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import time
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class TokenUsageEntry(TypedDict):
    timestamp: float
    description: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float

class TokenTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_calls = 0
        self.token_log: List[TokenUsageEntry] = []
        self.last_call_tokens = {
            "input": 0, 
            "output": 0, 
            "total": 0, 
            "cost": 0
        }
        self.input_cost_per_1k = 0.003
        self.output_cost_per_1k = 0.015

    def add_usage(self, input_tokens: int, output_tokens: int, description: str = "API call") -> None:
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
            "description": description
        }

        self.token_log.append({
            "timestamp": time.time(),
            "description": description,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": total_cost
        })



    def get_last_call_usage(self) -> Dict[str, Any]:
        return self.last_call_tokens

    def get_summary(self) -> Dict[str, Any]:
        total_tokens = self.total_input_tokens + self.total_output_tokens
        total_cost = ((self.total_input_tokens / 1000) * self.input_cost_per_1k + 
                      (self.total_output_tokens / 1000) * self.output_cost_per_1k)

        return {
            "api_calls": self.api_calls,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost": total_cost,
            "last_call": self.last_call_tokens,
            "token_history": self.token_log[-10:] if len(self.token_log) > 10 else self.token_log
        }

    def print_summary(self) -> None:
        summary = self.get_summary()

        print("\n" + "="*50)
        print(" TOKEN USAGE SUMMARY ")
        print("="*50)
        print(f"Total API calls: {summary['api_calls']}")
        print(f"Input tokens: {summary['input_tokens']:,}")
        print(f"Output tokens: {summary['output_tokens']:,}")
        print(f"Total tokens: {summary['total_tokens']:,}")
        print(f"Estimated cost: ${summary['estimated_cost']:.4f}")
        print("="*50)

    def reset(self) -> None:
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_calls = 0
        self.token_log = []
        self.last_call_tokens = {
            "input": 0, 
            "output": 0, 
            "total": 0, 
            "cost": 0
        }

class McpState:
    DISCONNECTED = 'disconnected'
    CONNECTING = 'connecting'
    CONNECTED = 'connected'
    INITIALIZING = 'initializing'
    INITIALIZED = 'initialized'
    ERROR = 'error'
    CLOSED = 'closed'

class MCPClient:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY environment variable not set")
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
            
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic(api_key=api_key)
        self.model_final = "claude-3-7-sonnet-20250219"
        
        self.token_tracker = TokenTracker()
        self.mcp_state = McpState.DISCONNECTED
        self.last_error = None
        self.tools_cache = []
        self.server_path = None
        self.connected_at = None
        self.debug_mode = False
        self.conversation_history = []
        self.system_prompt = self._create_optimized_system_prompt()
        
        self.request_queue = asyncio.Queue()
        self.response_map = {}
        self.request_lock = asyncio.Lock()
        self.worker_task = None
        self.next_request_id = 0

    # ==========================================================================
    # INITIALIZATION AND SYSTEM PROMPT
    # ==========================================================================
        
    def _create_optimized_system_prompt(self) -> str:
        return """
        You are an expert-level AI assistant specializing in data analysis and strategic insight generation using MCP tools. Your primary goal is to produce highly detailed, comprehensive, exceptionally well-written, and well-referenced reports based on user requests.

        **CORE OBJECTIVES:**
        1.  **Depth & Comprehensiveness:** Go beyond surface-level answers. Provide thorough analysis, exploring nuances, implications, and relevant context. Synthesize information from multiple tool calls if necessary to build a complete picture. Aim for substantial, informative responses.
        2.  **Clarity & Structure:** Present findings in a highly organized, professional format. Use clear headings, subheadings, bullet points, and potentially tables where appropriate. Ensure a logical flow from overview to specific details and insights.
        3.  **Insight Generation:** Do not just present raw data. Extract meaningful insights, identify trends, anomalies, potential causes, and strategic implications. Generate executive summaries that capture the essence of the findings.
        4.  **Professional Tone:** Maintain a formal, objective, and authoritative tone. Write clearly, concisely (within the context of being comprehensive), and use precise language.
        5.  **Source Transparency:** Ensure the origin of information is clear by referencing the source documents (tool outputs) used.

        **TOOL USAGE PROTOCOL:**
        - Autonomously determine and utilize the necessary MCP tools to gather all required data for a thorough analysis in response to the user's query.
        - Execute tool calls efficiently. Avoid unnecessary steps or narration about tool selection or execution.
        - If multiple data points or sources are needed, use tools comprehensively to acquire them before generating the final analysis. Ensure *all* relevant tool outputs are considered.

        **ANALYSIS & REPORTING GUIDELINES:**
        - **No Meta-Commentary:** Directly present the analysis and findings. Do *not* describe your internal thought process, planning stages, or intentions (e.g., avoid phrases like "I will now analyze...", "First, I need to...", "Looking at the data...").
        - **Structure:**
            - Start with a concise **Executive Summary** (unless inappropriate for the query length).
            - Use `## Major Section Heading` for distinct parts of the analysis.
            - Use `### Sub-Section Heading` for more granular topics.
            - Utilize bullet points (`- `) for key findings, data points, and insights within sections.
            - Ensure logical progression and coherence throughout the report.
        - **Content:**
            - Include specific data points, metrics, and evidence gathered from the tools.
            - **Source Attribution:** Explicitly reference or attribute information to the specific source documents (tool outputs) it was derived from. Make it clear which findings come from which sources, especially when synthesizing information. Aim to acknowledge *all* documents referenced in the generation of the report.
            - Elaborate on findings; explain *why* something might be significant.
            - Provide context where necessary for understanding.
            - Aim for exhaustive coverage of the user's request, supported by the gathered evidence.

        **FINAL IMPERATIVE:** Your output must be significantly detailed, demonstrably comprehensive, professionally structured, insightful, and clearly reference the underlying source documents (tool outputs). Assume the user requires a deep-dive analysis suitable for strategic decision-making. Deliver the complete analysis directly.
        """

    # ==========================================================================
    # MCP SERVER CONNECTION MANAGEMENT
    # ==========================================================================
        
    async def connect_to_server(self, server_script_path: str) -> None:
        self.server_path = server_script_path
        self.mcp_state = McpState.CONNECTING
        
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            self.mcp_state = McpState.ERROR
            self.last_error = "Server script must be a .py or .js file"
            raise ValueError(self.last_error)
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
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
        self.tools_cache = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in self.tools_cache])
        
        print("\n-----------------------------------------")
        print("Welcome to the Claude MCP Client")
        print("-----------------------------------------")
        print("Available tools:")
        for tool in self.tools_cache:
            print(f"• {tool.name}: {tool.description or 'No description'}")
        print("-----------------------------------------")
        
        self.worker_task = asyncio.create_task(self._process_queue())
    
    async def ensure_connection(self) -> bool:
        if self.session is None:
            logger.warning("No active session, cannot check connection health")
            return False
            
        try:
            await asyncio.wait_for(self.session.list_tools(), timeout=5.0)
            return True
        except Exception as e:
            logger.error("Connection health check failed: %s", str(e))
            return False
            
    async def reconnect(self) -> None:
        if not self.server_path:
            logger.error("No server path available for reconnection")
            raise RuntimeError("No server path available for reconnection")
            
        logger.info("Attempting to reconnect to server at %s", self.server_path)
        
        self.exit_stack = AsyncExitStack()
        self.session = None
        
        await self.connect_to_server(self.server_path)
        logger.info("Successfully reconnected to server")
    
    # ==========================================================================
    # ASYNC QUEUE PROCESSING
    # ==========================================================================
    
    async def _process_queue(self) -> None:
        """Background worker to process queued requests"""
        iteration_count = 0
        last_log_time = time.time()
        idle_count = 0
        max_sleep_time = 0.5  # Maximum sleep time in seconds
        
        while True:
            try:
                # Log every 1000 iterations
                iteration_count += 1
                current_time = time.time()
                if iteration_count % 1000 == 0 or current_time - last_log_time > 5:
                    logger.info(f"Worker iteration {iteration_count}, queue size: {self.request_queue.qsize()}, idle_count: {idle_count}")
                    last_log_time = current_time
                
                # Add adaptive sleep when queue is empty
                if self.request_queue.empty():
                    idle_count += 1
                    # Increase sleep time the longer we're idle, up to max_sleep_time
                    sleep_time = min(0.1 * min(idle_count, 5), max_sleep_time)
                    await asyncio.sleep(sleep_time)
                    continue
                
                # Reset idle count when we process something
                idle_count = 0
                
                request_id, tool_name, tool_args = await self.request_queue.get()
                
                try:
                    result = await asyncio.wait_for(
                        self.session.call_tool(tool_name, tool_args),
                        timeout=5.0
                    )
                    
                    self.response_map[request_id] = {
                        "success": True,
                        "result": result,
                        "tool": tool_name,
                        "args": tool_args
                    }
                    
                except Exception as e:
                    error_msg = f"Error executing {tool_name}: {str(e)}"
                    logger.error(error_msg)
                    self.response_map[request_id] = {
                        "success": False,
                        "error": error_msg,
                        "tool": tool_name,
                        "args": tool_args
                    }
                    
                finally:
                    self.request_queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue worker: {str(e)}")
                await asyncio.sleep(1)
    
    async def process_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        results = []
        pending_requests = []
        
        async with self.request_lock:
            for content in tool_calls:
                tool_name = content.name
                tool_args = content.input
                request_id = str(self.next_request_id)
                self.next_request_id += 1
                
                await self.request_queue.put((request_id, tool_name, tool_args))
                
                pending_requests.append({
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_use_id": content.id
                })
        
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
                    results.append({
                        "tool": req["tool_name"],
                        "args": req["tool_args"],
                        "result": response["result"],
                        "success": True,
                        "tool_use_id": req["tool_use_id"]
                    })
                else:
                    results.append({
                        "tool": req["tool_name"],
                        "args": req["tool_args"],
                        "error": response["error"],
                        "success": False,
                        "tool_use_id": req["tool_use_id"]
                    })
            else:
                results.append({
                    "tool": req["tool_name"],
                    "args": req["tool_args"],
                    "error": "Request timed out",
                    "success": False,
                    "tool_use_id": req["tool_use_id"]
                })
        
        return results

    # ==========================================================================
    # CLAUDE API INTEGRATION
    # ==========================================================================

    async def call_with_backoff(self, func: Callable, *args: Any, max_retries: int = 3, 
                               initial_delay: float = 1.0, **kwargs: Any) -> Any:
        delay = initial_delay
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if func.__module__.startswith('anthropic'):
                    return func(*args, **kwargs)
                else:
                    return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                logger.warning("Call failed on attempt %d/%d: %s", 
                            attempt+1, max_retries, str(e))
                
                if attempt < max_retries - 1:
                    sleep_time = delay * (2 ** attempt)
                    logger.info("Retrying in %.1f seconds...", sleep_time)
                    await asyncio.sleep(sleep_time)
        
        logger.error("All %d attempts failed", max_retries)
        raise last_exception
        
    async def call_claude_with_fallback(self, messages: List[Dict[str, Any]], 
                                      system: Optional[str] = None, 
                                      tools: Optional[List[Dict[str, Any]]] = None, 
                                      max_tokens: Optional[int] = None, 
                                      temperature: Optional[float] = None,
                                      model: Optional[str] = None) -> Any:
        try:
            params = {
                "model": model or "claude-3-5-sonnet-20240620",
                "max_tokens": max_tokens or 8000,
                "messages": messages,
                "temperature": temperature or 0.2
            }
            
            if system:
                params["system"] = system
            
            if tools and isinstance(tools, list) and len(tools) > 0:
                params["tools"] = tools
            
            return self.anthropic.messages.create(**params)
        
        except Exception as primary_error:
            logger.error("Primary Claude call failed: %s", str(primary_error))
            
            try:
                logger.info("Trying fallback to Claude 3 Sonnet")
                fallback_params = {
                    "model": "claude-3-5-sonnet-20240620",
                    "max_tokens": max_tokens or 4000,
                    "messages": messages,
                    "temperature": 0.2
                }
                
                if system:
                    fallback_params["system"] = system
                
                if tools and isinstance(tools, list) and len(tools) > 0:
                    fallback_params["tools"] = tools
                
                return self.anthropic.messages.create(**fallback_params)
            
            except Exception as model_fallback_error:
                logger.error("Model fallback call failed: %s", str(model_fallback_error))
            
            if tools:
                try:
                    logger.info("Trying fallback without tools")
                    return self.anthropic.messages.create(
                        model="claude-3-5-sonnet-20240620",
                        max_tokens=max_tokens or 4000,
                        messages=messages,
                        system=system if system else None,
                        temperature=0.2
                    )
                except Exception as fallback_error:
                    logger.error("Fallback Claude call also failed: %s", str(fallback_error))
            
            raise primary_error

    # ==========================================================================
    # CONVERSATION MANAGEMENT
    # ==========================================================================
            
    async def manage_context(self) -> None:
        if len(self.conversation_history) <= 10:
            return
            
        keep_count = 8
        important_context = []
        
        if self.conversation_history:
            important_context.append(self.conversation_history[0])
        
        important_context.extend(self.conversation_history[-keep_count:])
        self.conversation_history = important_context

    async def process_query(self, query: str) -> str:
        self.conversation_history.append({
            "role": "user",
            "content": query
        })
        
        await self.manage_context()
        
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        
        print("\nAnalyzing your request...")
        
        casual_check_system = """
        You are classifying the type of query. For this response ONLY:
        - If the user's message is casual conversation (like "how are you?", greetings, etc.), respond with "CASUAL_CONVERSATION"
        - If the user is asking for help or information about this system, respond with "HELP_REQUEST"
        - If the user is asking for information that requires data access or analysis, respond with "ANALYSIS_NEEDED"
        
        Respond with just one of these classifications and nothing else.
        """
        
        initial_response = await self.call_claude_with_fallback(
            messages=[{"role": "user", "content": query}],
            system=casual_check_system,
            max_tokens=50
        )
        
        self.token_tracker.add_usage(
            initial_response.usage.input_tokens,
            initial_response.usage.output_tokens,
            "Query Classification"
        )
        
        classification = ""
        for content in initial_response.content:
            if content.type == 'text':
                classification = content.text.strip().upper()
                break
        
        if "CASUAL_CONVERSATION" in classification:
            return await self._handle_casual_conversation(query)
        elif "HELP_REQUEST" in classification:
            return await self._handle_help_request(query)
        else:
            print("\n📊 Starting strategic analysis process...")
            return await self.strategic_analysis(query)

    async def _handle_casual_conversation(self, query: str) -> str:
        print("\n💬 Casual conversation detected - responding directly...")
        
        system_prompt = """
        You are a friendly, conversational assistant. For casual conversations:
        - Respond naturally and engagingly
        - Keep responses concise (1-3 sentences)
        - Be warm and personable
        - Don't suggest using tools unless specifically asked
        """
        
        response = await self.call_claude_with_fallback(
            messages=self.conversation_history,
            system=system_prompt,
            max_tokens=300,
            temperature=0.7
        )
        
        self.token_tracker.add_usage(
            response.usage.input_tokens,
            response.usage.output_tokens,
            "Casual Conversation"
        )
        
        text_content = []
        for content in response.content:
            if content.type == 'text':
                text_content.append(content.text)
        
        reply = "\n".join(text_content)
        
        self.conversation_history.append({
            "role": "assistant",
            "content": response.content
        })
        
        return reply

    async def _handle_help_request(self, query: str) -> str:
        print("\n📚 Help request detected - providing system information...")
        
        system_prompt = """
        You are explaining how this MCP client works. Your explanation should:
        - Describe the system's capabilities in simple terms
        - Explain how users can interact with data and documents
        - Suggest sample queries the user might try
        - Be helpful and concise
        """
        
        response = await self.call_claude_with_fallback(
            messages=self.conversation_history,
            system=system_prompt,
            max_tokens=800,
            temperature=0.3
        )
        
        self.token_tracker.add_usage(
            response.usage.input_tokens,
            response.usage.output_tokens,
            "Help Request"
        )
        
        text_content = []
        for content in response.content:
            if content.type == 'text':
                text_content.append(content.text)
        
        reply = "\n".join(text_content)
        
        self.conversation_history.append({
            "role": "assistant",
            "content": response.content
        })
        
        return reply

    # ==========================================================================
    # STRATEGIC ANALYSIS
    # ==========================================================================

    async def strategic_analysis(self, query: str) -> str:
        self.conversation_history.append({
            "role": "user",
            "content": query
        })
        
        self._report_progress("Analyzing your request...")
        
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]
        
        tool_descriptions = "\n".join([
            f"- {tool['name']}: {tool['description'] or 'No description'}" 
            for tool in available_tools
        ])
        
        self._report_progress("Phase 1: Developing analysis strategy...")
        
        planning_system_prompt = f"""
        You are developing a strategic plan to answer the user's query.
        Your task is to:
        1. Analyze what information is needed to fully answer the query
        2. Determine which specific tools should be used in which order
        3. Create a step-by-step plan with EXACTLY 3-4 steps (no more than 4)
        
        IMPORTANT: You must ONLY use tools that are actually available. Here are the tools you can use:
        
        {tool_descriptions}
        
        DO NOT reference tools that are not in this list. DO NOT make up tools that don't exist.
        DO NOT execute any tools yet. Just create a detailed plan.
        
        FORMAT YOUR RESPONSE AS:
        
        ## Analysis Strategy
        [1-2 sentences explaining your overall approach]
        
        ## Step-by-Step Plan
        1. [Step description using ONLY tool names from the list above]
        2. [Step description using ONLY tool names from the list above]
        ...
        
        REMEMBER: 
        - Maximum 4 steps in your plan
        - Only reference tools that actually exist in the list above
        - Be specific about which tool to use in each step
        """
        
        planning_response = await self.call_claude_with_fallback(
            messages=list(self.conversation_history) + [{
                "role": "user",
                "content": "Before answering my query, develop a strategic plan outlining what information you need to gather and in what order. What specific steps will you take to answer my query comprehensively?"
            }],
            system=planning_system_prompt,
            max_tokens=1000
        )
        
        self.token_tracker.add_usage(
            planning_response.usage.input_tokens,
            planning_response.usage.output_tokens,
            "Strategy Planning"
        )
        
        strategy_text = ""
        if hasattr(planning_response, 'content'):
            for content in planning_response.content:
                if hasattr(content, 'type') and content.type == 'text':
                    strategy_text += content.text
        elif hasattr(planning_response, 'completion'):
            strategy_text = planning_response.completion
        else:
            strategy_text = str(planning_response)

        steps = self._parse_strategy_steps(strategy_text)
        total_steps = len(steps)
        
        formatted_plan = f"""
        ## Analysis Strategy and Step-by-Step Plan
        {strategy_text}
        """
        self._report_progress(formatted_plan)
        
        execution_history = [
            {
                "role": "user",
                "content": f"{query}\n\nI'll analyze this using the following plan:\n\n{strategy_text}"
            }
        ]
        
        self._report_progress("Phase 2: Executing analysis plan...")
        
        all_results = []
        for i, step in enumerate(steps):
            step_message = f"Executing Step {i+1}/{total_steps}: {step['description']}"
            self._report_progress(step_message)
            
            execution_system_prompt = f"""
            You are executing a specific step in an analysis plan.
            Focus ONLY on executing the current step using the appropriate tool.

            Available tools:
            {tool_descriptions}

            ONLY use tools from this list. DO NOT provide analysis yet - just execute the tool call needed for this step.
            """
            
            execution_response = await self.call_claude_with_fallback(
                messages=execution_history + [{"role": "user", "content": step_message}],
                system=execution_system_prompt,
                tools=available_tools,
                max_tokens=1000
            )
            
            tool_calls = [content for content in execution_response.content 
                        if content.type == 'tool_use']
            
            if tool_calls:
                step_results = await self.process_tool_calls(tool_calls)
                all_results.extend(step_results)
                
                self._report_progress(f"Successfully retrieved data for step {i+1}")
                
                for result in step_results:
                    if result["success"]:
                        execution_history.append({
                            "role": "assistant",
                            "content": [{"type": "tool_use", "id": result["tool_use_id"], "name": result["tool"], "input": result["args"]}]
                        })
                        execution_history.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": result["tool_use_id"],
                                    "content": result["result"].content
                                }
                            ]
                        })
                    else:
                        execution_history.append({
                            "role": "assistant",
                            "content": [{"type": "tool_use", "id": result["tool_use_id"], "name": result["tool"], "input": result["args"]}]
                        })
                        execution_history.append({
                            "role": "user",
                            "content": f"Error when executing tool: {result['error']}"
                        })
        
        self._report_progress("Phase 3: Synthesizing final analysis...")
        
        synthesis_system_prompt = """
        You are creating a comprehensive final analysis based on all the data gathered.
        
        Use all the information collected in the previous steps to create a cohesive, 
        well-structured response that fully answers the user's original query.
        
        Your analysis should:
        - Begin with key findings and highlights
        - Include clear section headings (## Heading)
        - Provide specific data points and metrics
        - Connect insights across different data sources
        - Present information in a logical flow
        
        Be comprehensive but focused. Include only information that helps answer the query."""
        
        synthesis_response = await self.call_claude_with_fallback(
            messages=execution_history + [{
                "role": "user",
                "content": "Now that you've gathered all the necessary information, please provide a comprehensive analysis that answers my original query."
                
            }],
            model=self.model_final,
            system=synthesis_system_prompt,
            max_tokens=4000
        )
        
        self.token_tracker.add_usage(
            synthesis_response.usage.input_tokens,
            synthesis_response.usage.output_tokens,
            "Final Synthesis"
        )
        
        final_text = []
        for content in synthesis_response.content:
            if content.type == 'text':
                final_text.append(content.text)
        
        final_analysis = "\n".join(final_text)
        
        self.conversation_history.append({
            "role": "assistant",
            "content": final_analysis
        })
        
        return final_analysis

    def _parse_strategy_steps(self, strategy_text: str) -> List[Dict[str, Any]]:
        steps = []
        lines = strategy_text.split('\n')
        
        for line in lines:
            match = re.match(r'^\s*(\d+)\.\s+(.*)', line)
            if match:
                number = int(match.group(1))
                description = match.group(2).strip()
                steps.append({
                    "number": number,
                    "description": description
                })
        
        return steps



    # ==========================================================================
    # TOOL UTILITIES AND FORMATTING
    # ==========================================================================
    
    def generate_test_args(self, input_schema: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        if not input_schema:
            return {}
            
        try:
            schema = json.loads(input_schema) if isinstance(input_schema, str) else input_schema
            result = {}
            
            if "properties" in schema and "required" in schema:
                for prop_name in schema.get("required", []):
                    if prop_name in schema.get("properties", {}):
                        prop_schema = schema["properties"][prop_name]
                        
                        if prop_schema.get("type") == "string":
                            result[prop_name] = "test"
                        elif prop_schema.get("type") in ["number", "integer"]:
                            result[prop_name] = 1
                        elif prop_schema.get("type") == "boolean":
                            result[prop_name] = False
                        elif prop_schema.get("type") == "array":
                            result[prop_name] = []
                        elif prop_schema.get("type") == "object":
                            result[prop_name] = {}
            
            return result
        except Exception as e:
            logger.error("Error generating test args: %s", str(e))
            return {}
    
    def get_generic_sql_description(self, query: str) -> str:
        query = query.lower()
        
        table_match = re.search(r'from\s+([a-z0-9_]+)', query)
        table = table_match.group(1) if table_match else "data"
        
        if "count(*)" in query:
            return f"Count analysis of {table}"
        elif "sum(" in query:
            return f"Total calculation for {table}"
        elif "avg(" in query or "average(" in query:
            return f"Average calculation for {table}"
        elif "group by" in query:
            group_match = re.search(r'group by\s+([a-z0-9_]+)', query)
            group = group_match.group(1) if group_match else "category"
            return f"Grouping {table} by {group}"
        else:
            return f"General query on {table}"
        
    
    # ==========================================================================
    # SERVER DIAGNOSTICS
    # ==========================================================================
            
    async def diagnose_server(self) -> Dict[str, Any]:
        diag_results = {
            "connection_state": self.mcp_state,
            "last_error": self.last_error,
            "tools_available": 0,
            "connected_since": self.connected_at if hasattr(self, "connected_at") else None,
            "tool_calls_successful": 0,
            "tool_calls_failed": 0
        }
        
        if self.mcp_state == McpState.INITIALIZED:
            try:
                tools_response = await asyncio.wait_for(self.session.list_tools(), timeout=5.0)
                diag_results["tools_available"] = len(tools_response.tools)
                diag_results["tool_names"] = [t.name for t in tools_response.tools]
                
                if tools_response.tools:
                    test_tool = tools_response.tools[0]
                    test_args = self.generate_test_args(test_tool.inputSchema)
                    
                    try:
                        await asyncio.wait_for(self.session.call_tool(test_tool.name, test_args), timeout=10.0)
                        diag_results["tool_calls_successful"] = 1
                    except Exception as e:
                        diag_results["tool_calls_failed"] = 1
                        diag_results["tool_call_error"] = str(e)
                
            except Exception as e:
                diag_results["diagnostic_error"] = str(e)
        
        return diag_results

    # ==========================================================================
    # PROGRESS REPORTING
    # ==========================================================================

    def set_progress_callback(self, callback: Callable) -> None:
        self._progress_callback = callback

    def _report_progress(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        if hasattr(self, '_progress_callback') and callable(self._progress_callback):
            self._progress_callback(message, details)
        else:
            print(message)

    
    # ==========================================================================
    # CLEANUP
    # ==========================================================================
    
    async def cleanup(self) -> None:
        self.mcp_state = McpState.CLOSED
        
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        
        try:
            if self.exit_stack:
                await self.exit_stack.aclose()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            self.exit_stack = AsyncExitStack()
            self.session = None


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await client.connect_to_server(sys.argv[1])
                break
            except Exception as e:
                logger.error("Connection attempt %d failed: %s", attempt+1, str(e), exc_info=True)
                if attempt == max_retries - 1:
                    print(f"Failed to connect after {max_retries} attempts. Exiting.")
                    sys.exit(1)
                print(f"Connection attempt {attempt+1} failed. Retrying in 2 seconds...")
                await asyncio.sleep(2)
                
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())