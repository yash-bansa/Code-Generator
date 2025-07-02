import asyncio
import sys
import logging
from typing import Dict, Any, List
from agents import CommunicationAgent,QueryRephraserAgent
from config.agents_io import CommunicationOutput, CommunicationInput, QueryEnhancerInput, QueryEnhancerOutput

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("langraph_query_flow.log")
    ]
)
logger = logging.getLogger(__name__)

# ---------- BotState Definition ----------
BotState = Dict[str, Any]

# ---------- Agent Initialization ----------
print("\n🤖 Initializing LangGraph-style Query Agents...")
print("=" * 60)

try:
    communication_agent = CommunicationAgent()
    query_rephraser_agent = QueryRephraserAgent()
    print("✅ Agents initialized successfully!")
except Exception as e:
    print(f"❌ Failed to initialize agents: {e}")
    sys.exit(1)

# ---------- LangGraph-Compatible Nodes ----------
async def communication_node(state: BotState) -> BotState:
    """LangGraph node: Extract core intent and context"""
    try:
        logger.info("🧠 Communication Node: Extracting intent...")

        comm_input = CommunicationInput(
            user_query=state["latest_query"],
            conversation_history=state.get("user_history", [])[:-1]
        )
        result: CommunicationOutput = await communication_agent.extract_intent(comm_input)

        state["core_intent"] = result.core_intent
        state["context_notes"] = result.context_notes
        state["communication_success"] = result.success

        logger.info(f"✅ Core Intent: {result.core_intent}")
        logger.info(f"📝 Context Notes: {result.context_notes}")
        return state

    except Exception as e:
        logger.error(f"❌ Communication node error: {e}")
        state["core_intent"] = state.get("latest_query", "")
        state["context_notes"] = f"[Error in communication processing: {str(e)}]"
        state["communication_success"] = False
        return state


async def query_enhancement_node(state: BotState) -> BotState:
    """LangGraph node: Enhance and validate developer task"""
    try:
        logger.info("🔧 Query Enhancement Node: Rephrasing and validating...")

        enhancer_input = QueryEnhancerInput(
            core_intent=state["core_intent"],
            context_notes=state["context_notes"]
        )
        result: QueryEnhancerOutput = await query_rephraser_agent.enhance_query(enhancer_input)

        state["developer_task"] = result.developer_task
        state["is_satisfied"] = result.is_satisfied
        state["suggestions"] = result.suggestions
        state["enhancement_success"] = result.success

        logger.info(f"🎯 Developer Task: {result.developer_task}")
        logger.info(f"✅ Is Satisfied: {result.is_satisfied}")
        if not result.is_satisfied:
            logger.info("💡 Suggestions:")
            for s in result.suggestions:
                logger.info(f"- {s}")
        return state

    except Exception as e:
        logger.error(f"❌ Query enhancement node error: {e}")
        state["developer_task"] = state.get("core_intent", "")
        state["is_satisfied"] = False
        state["suggestions"] = [f"Error processing query: {str(e)}"]
        state["enhancement_success"] = False
        return state

# ---------- Run LangGraph-like Flow ----------
async def main():
    print("\nWelcome to the LangGraph Query Clarifier")
    print("=" * 60)

    history: List[str] = []

    while True:
        user_query = input("\n💬 Describe your task (or type 'exit'): ").strip()
        if not user_query:
            print("⚠️ Please enter a valid input.")
            continue
        if user_query.lower() in ["exit", "quit"]:
            print("👋 Exiting...")
            break

        history.append(user_query)

        # Initial State
        state: BotState = {
            "latest_query": user_query,
            "user_history": history,
            "core_intent": "",
            "context_notes": "",
            "developer_task": "",
            "is_satisfied": False,
            "suggestions": [],
        }

        # STEP 1: Communication Agent
        state = await communication_node(state)

        # STEP 2: Query Rephrase Agent
        state = await query_enhancement_node(state)

        # Final output
        print("\n📌 Final Output")
        print("=" * 40)
        print(f"🧠 Core Intent: {state['core_intent']}")
        print(f"📝 Context: {state['context_notes']}")
        print(f"🎯 Developer Task: {state['developer_task']}")
        print(f"✅ Satisfied: {state['is_satisfied']}")
        if not state['is_satisfied']:
            print("💡 Suggestions:")
            for s in state["suggestions"]:
                print(f"- {s}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
