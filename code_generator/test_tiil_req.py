import asyncio
import sys
import logging
from langgraph.graph import StateGraph
from typing import List, Union
from pydantic import BaseModel

from agents import CommunicationAgent, QueryRephraserAgent
from config.agents_io import (
    BotStateSchema,
    CommunicationInput,
    CommunicationOutput,
    QueryEnhancerInput,
    QueryEnhancerOutput
)

# ---------- Logging Setup ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("langraph_query_flow.log")
    ]
)
logger = logging.getLogger(__name__)

# ---------- Agent Initialization ----------
print("\nInitializing LangGraph-style Query Agents...")
communication_agent = CommunicationAgent()
query_rephraser_agent = QueryRephraserAgent()
print("Agents initialized successfully!")

# ---------- Helper to ensure correct schema ----------
def ensure_state_schema(state: Union[dict, BaseModel]) -> BotStateSchema:
    if isinstance(state, BotStateSchema):
        return state
    return BotStateSchema(**state)

# ---------- LangGraph-Compatible Nodes ----------
async def communication_node(state: dict) -> dict:
    state_obj = ensure_state_schema(state)
    logger.info("Communication Node: Extracting intent...")

    comm_input = CommunicationInput(
        user_query=state_obj.latest_query,
        conversation_history=state_obj.user_history[:-1] if len(state_obj.user_history) > 1 else []
    )
    result: CommunicationOutput = await communication_agent.extract_intent(comm_input)

    state_obj.core_intent = result.core_intent
    state_obj.context_notes = result.context_notes
    state_obj.communication_success = result.success

    logger.info(f"Core Intent: {result.core_intent}")
    logger.info(f"Context Notes: {result.context_notes}")
    return state_obj.dict()

async def query_enhancement_node(state: dict) -> dict:
    state_obj = ensure_state_schema(state)
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

    logger.info(f"Developer Task: {result.developer_task}")
    logger.info(f"Is Satisfied: {result.is_satisfied}")
    if not result.is_satisfied:
        logger.info("Suggestions:")
        for s in result.suggestions:
            logger.info(f"- {s}")

    return state_obj.dict()

# ---------- Run LangGraph Flow ----------
async def main():
    print("\nWelcome to the LangGraph Query Clarifier")
    print("=" * 60)

    history: List[str] = []

    while True:
        user_query = input("\nDescribe your task (or type 'exit'): ").strip()
        if not user_query:
            print("Please enter a valid input.")
            continue
        if user_query.lower() in ["exit", "quit"]:
            print("Exiting...")
            break

        history.append(user_query)
        state = BotStateSchema(
            latest_query=user_query,
            user_history=history
        )

        # Build LangGraph
        builder = StateGraph(dict)
        builder.add_node("communication_node", communication_node)
        builder.add_node("query_enhancement_node", query_enhancement_node)
        builder.set_entry_point("communication_node")
        builder.add_edge("communication_node", "query_enhancement_node")
        builder.set_finish_point("query_enhancement_node")
        graph = builder.compile()

        print("\nLangGraph Structure:")
        try:
            ascii_art = graph.get_graph().draw_ascii()
            print(ascii_art)
        except Exception as e:
            logger.warning(f"Unable to draw graph structure: {e}")

        # Run the graph
        final_state_dict = await graph.ainvoke(state.dict())
        final_state = BotStateSchema(**final_state_dict)

        # Output
        print("\nFinal Output")
        print("=" * 40)
        print(f"Core Intent: {final_state.core_intent}")
        print(f"Context: {final_state.context_notes}")
        print(f"Developer Task: {final_state.developer_task}")
        print(f"Satisfied: {final_state.is_satisfied}")
        if not final_state.is_satisfied:
            print("Suggestions:")
            for s in final_state.suggestions:
                print(f"- {s}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
