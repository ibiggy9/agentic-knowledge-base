from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Optional, Any, List, Literal
import uuid
import asyncio
import os
import json
import logging
import traceback
from dotenv import load_dotenv
from pathlib import Path
from .client_gemini import MCPClient as GeminiClient
import time
import re
from contextlib import asynccontextmanager
import uvicorn

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    for session_id, client in list(active_sessions.items()):
        try:
            await client.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {str(e)}")

    active_sessions.clear()
    session_types.clear()


app = FastAPI(title="Agentic AI Platform API", lifespan=lifespan)

# Configure CORS from environment for safer defaults
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
allowed_origins = (
    [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
    if allowed_origins_env
    else ["http://localhost:3000", "http://127.0.0.1:3000"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InitRequest(BaseModel):
    server_type: Literal["rfx", "samsara", "raw_rfx"] = "rfx"
    session_id: Optional[str] = None


class QueryRequest(BaseModel):
    session_id: str
    query: str


class ApiResponse(BaseModel):
    status: str
    message: Optional[str] = None
    response: Optional[str] = None


active_sessions: Dict[str, Any] = {}
session_types: Dict[str, str] = {}

SERVER_PATHS = {
    "rfx": "./backend/agents/rfx_analyzer/mcp-server_rfx/server_test.py",
    "samsara": "./backend/agents/samsara_integration/mcp_server_samsara/server.py",
    "raw_rfx": "./backend/agents/raw_data_processor/mcp_server_rfx_raw_data/server.py",
}


async def load_mcp_client(server_type: str):
    try:
        client = GeminiClient()

        server_path = SERVER_PATHS.get(server_type)
        if not server_path:
            raise ValueError(f"Unknown server type: {server_type}")

        await client.connect_to_server(server_path)

        return client
    except Exception as e:
        import traceback

        full_traceback = traceback.format_exc()
        logger.error(f"Full traceback: {full_traceback}")
        raise Exception(
            f"Error initializing MCPClient: {str(e)}\nFull traceback: {full_traceback}"
        )


@app.post("/api/init", response_model=ApiResponse)
async def initialize_session(request: InitRequest):
    try:
        session_id = request.session_id or str(uuid.uuid4())

        if session_id in active_sessions:
            try:
                await active_sessions[session_id].cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up existing session: {str(e)}")

        logger.info(
            f"Initializing {request.server_type} server with session {session_id}"
        )

        try:
            client = await load_mcp_client(request.server_type)
        except Exception as e:
            logger.error(f"Client initialization failed: {str(e)}")
            if "anyio" in str(e).lower() or "subscriptable" in str(e).lower():
                logger.error(
                    "This appears to be an anyio compatibility issue. Check your package versions."
                )
                return {
                    "status": "error",
                    "message": f"Failed to initialize session due to library compatibility issues: {str(e)}. Please check server logs.",
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to initialize session: {str(e)}",
                }

        active_sessions[session_id] = client
        session_types[session_id] = request.server_type

        tools = []
        try:
            response = await client.session.list_tools()
            tools = [tool.name for tool in response.tools]
        except Exception as e:
            logger.warning(f"Error fetching tools: {str(e)}")

        return {
            "status": "connected",
            "message": f"Session initialized successfully with {request.server_type} server",
            "response": json.dumps(
                {
                    "session_id": session_id,
                    "server_type": request.server_type,
                    "available_tools": tools,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Error initializing session: {str(e)}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Failed to initialize session: {str(e)}"}


@app.get("/api/server-types")
async def get_server_types():
    return {
        "server_types": [
            {
                "id": "rfx",
                "name": "RFX Database",
                "description": "Analyze RFX database with SQL queries",
            },
            {
                "id": "samsara",
                "name": "Samsara Analysis",
                "description": "Analyze Samsara documents from Google Drive",
            },
            {
                "id": "raw_rfx",
                "name": "Raw RFX Data",
                "description": "Analyze individual RFX sales calls and RFP requests",
            },
        ]
    }


@app.post("/api/query", response_model=ApiResponse)
async def process_query(request: QueryRequest):
    try:
        if request.session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        client = active_sessions[request.session_id]

        logger.info(
            f"Processing query for session {request.session_id}: {request.query}"
        )

        response = await client.process_query(request.query)

        return {"status": "success", "response": response}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        logger.error(traceback.format_exc())
        return {"status": "error", "message": f"Failed to process query: {str(e)}"}


@app.get("/api/query-stream")
async def stream_query(session_id: str = Query(...), query: str = Query(...)):
    async def event_generator():
        try:
            if session_id not in active_sessions:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
                return

            client = active_sessions[session_id]

            yield f"data: {json.dumps({'type': 'progress', 'message': 'Analyzing your request...'})}\n\n"

            progress_queue = asyncio.Queue()

            processing_complete = False
            final_response_sent = False

            async def process_query_task():
                nonlocal processing_complete
                nonlocal final_response_sent
                try:

                    def progress_callback(message, details=None):
                        modified_details = details.copy() if details else {}

                        if "Successfully" in message and "step" in message.lower():
                            step_match = re.search(
                                r"step\s+(\d+)", message, re.IGNORECASE
                            )
                            if step_match:
                                step_num = int(step_match.group(1))
                                modified_details["status"] = "completed"
                                modified_details["step"] = step_num
                                print(f"Setting step {step_num} as completed")

                        asyncio.create_task(
                            progress_queue.put(
                                {
                                    "type": "progress",
                                    "message": message,
                                    "details": modified_details,
                                    "metrics": (
                                        modified_details.get("metrics")
                                        if modified_details
                                        else None
                                    ),
                                    "timestamp": time.time(),
                                }
                            )
                        )

                    if hasattr(client, "set_progress_callback"):
                        client.set_progress_callback(progress_callback)

                    response = await client.process_query(query)

                    await progress_queue.put(
                        {
                            "type": "final",
                            "response": response,
                            "timestamp": time.time(),
                        }
                    )
                    final_response_sent = True

                except Exception as e:
                    logger.error(f"Error processing streamed query: {str(e)}")
                    logger.error(traceback.format_exc())
                    await progress_queue.put(
                        {
                            "type": "error",
                            "message": f"Error processing query: {str(e)}",
                            "timestamp": time.time(),
                        }
                    )
                    final_response_sent = True
                finally:
                    processing_complete = True

            process_task = asyncio.create_task(process_query_task())

            consecutive_timeouts = 0
            max_consecutive_timeouts = 3
            timeout_seconds = 20.0

            while not (
                processing_complete and progress_queue.empty() and final_response_sent
            ):
                try:
                    result = await asyncio.wait_for(
                        progress_queue.get(), timeout=timeout_seconds
                    )
                    consecutive_timeouts = 0

                    yield f"data: {json.dumps(result)}\n\n"

                    if result.get("type") in ["final", "error"]:
                        final_response_sent = True

                except asyncio.TimeoutError:
                    consecutive_timeouts += 1

                    keepalive_data = {
                        "type": "keepalive",
                        "consecutive_timeouts": consecutive_timeouts,
                        "processing_complete": processing_complete,
                        "queue_empty": progress_queue.qsize() == 0,
                        "final_sent": final_response_sent,
                        "timestamp": time.time(),
                    }
                    keepalive_json = json.dumps(keepalive_data)
                    yield f"data: {keepalive_json}\n\n"

                    if (
                        consecutive_timeouts >= max_consecutive_timeouts
                        and processing_complete
                    ):
                        logger.warning(
                            f"Stream ended after {consecutive_timeouts} consecutive timeouts"
                        )

                        if not final_response_sent:
                            error_data = {
                                "type": "error",
                                "message": "Analysis timed out or disconnected. Please try again.",
                                "timestamp": time.time(),
                            }
                            error_json = json.dumps(error_data)
                            yield f"data: {error_json}\n\n"
                        break

            if not process_task.done():
                process_task.cancel()
                try:
                    await process_task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"Error in event stream: {str(e)}")
            logger.error(traceback.format_exc())
            yield f"data: {json.dumps({'type': 'error', 'message': f'Stream error: {str(e)}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "version": "1.0.0",
    }


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    if session_id in active_sessions:
        try:
            await active_sessions[session_id].cleanup()
        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            del active_sessions[session_id]
            if session_id in session_types:
                del session_types[session_id]

    return {"status": "success", "message": "Session deleted"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
