import asyncio
import sys
import logging, warnings
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import redis
from config.settings import settings
from langgraph.graph import StateGraph
from agents import CommunicationAgent, QueryRephraserAgent
from config.agents_io import (
    BotStateSchema,
    CommunicationInput,
    CommunicationOutput,
    QueryEnhancerInput,
    QueryEnhancerOutput
)

# ---------------- Logging Setup ----------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("langraph_query_flow.log")
    ]
)
logger = logging.getLogger(__name__)

# ----------- Redis Connection ------------------

redis_client = settings.get_redis_connection()

# ---------------- Agent Initialization ----------------
communication_agent = CommunicationAgent()
query_rephraser_agent = QueryRephraserAgent()

# ---------------- Input Schema ----------------
class QueryPayload(BaseModel):
    user_id: str
    user_query: str

# ---------------- LangGraph Nodes ----------------
async def communication_node(state: dict) -> dict:
    state_obj = BotStateSchema(**state)
    logger.info("Communication Node: Extracting intent...")

    comm_input = CommunicationInput(
        user_query=state_obj.latest_query,
        conversation_history=state_obj.user_history[:-1] if len(state_obj.user_history) > 1 else []
    )
    result: CommunicationOutput = await communication_agent.extract_intent(comm_input)

    state_obj.core_intent = result.core_intent
    state_obj.context_notes = result.context_notes
    state_obj.communication_success = result.success

    return state_obj.dict()

async def query_enhancement_node(state: dict) -> dict:
    state_obj = BotStateSchema(**state)
    logger.info("Query Enhancement Node: Rephrasing and validating...")

    enhancer_input = QueryEnhancerInput(
        core_intent=state_obj.core_intent,
        context_notes=state_obj.context_notes
    )
    result: QueryEnhancerOutput = await query_rephraser_agent.enhance_query(enhancer_input)

    state_obj.developer_task = result.developer_task
    state_obj.is_satisfied = result.is_satisfied
    state_obj.suggestions = result.suggestions
    state_obj.enhancement_success = result.success

    return state_obj.dict()

# ---------------- LangGraph Flow ----------------
builder = StateGraph(dict)
builder.add_node("communication_node", communication_node)
builder.add_node("query_enhancement_node", query_enhancement_node)
builder.set_entry_point("communication_node")
builder.add_edge("communication_node", "query_enhancement_node")
builder.set_finish_point("query_enhancement_node")
graph = builder.compile()

# ---------------- FastAPI Setup ----------------
app = FastAPI(title="LangGraph Query Clarifier with Redis")

@app.post("/process-query")
async def process_query(payload: QueryPayload):
    user_id = payload.user_id
    user_query = payload.user_query
    history_key = f"user:{user_id}:history"

    # Get user history from Redis
    history = redis_client.lrange(history_key, 0, -1)
    redis_client.rpush(history_key, user_query)  # Append new query

    # Build initial state
    state = BotStateSchema(
        latest_query=user_query,
        user_history=history + [user_query]
    )

    final_state_dict = await graph.ainvoke(state.dict())
    final_state = BotStateSchema(**final_state_dict)

    return {
        "core_intent": final_state.core_intent,
        "context": final_state.context_notes,
        "developer_task": final_state.developer_task,
        "is_satisfied": final_state.is_satisfied,
        "suggestions": final_state.suggestions if not final_state.is_satisfied else []
    }

@app.delete("/clear-session/{user_id}")
def clear_session(user_id: str):
    history_key = f"user:{user_id}:history"
    if redis_client.exists(history_key):
        redis_client.delete(history_key)
        return {"message": f"Session for user '{user_id}' cleared from Redis."}
    raise HTTPException(status_code=404, detail=f"No session found for user '{user_id}'")

