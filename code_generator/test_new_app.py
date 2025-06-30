import streamlit as st
import json
import sys
import asyncio
from pathlib import Path
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from agents.QueryRephraseAgent import QueryRephraseAgent
from agents.parser_agent import ParserAgent
from agents.master_planner_agent import MasterPlannerAgent
from agents.delta_analyzer_agent import DeltaAnalyzerAgent
from agents.code_generator_agent import CodeGeneratorAgent
from config.settings import settings
import copy

# Add root path if necessary
sys.path.append(str(Path(__file__).resolve().parents[1]))

# ---------- State Definition ----------
class BotState(TypedDict):
    user_history: List[str]
    latest_query: str
    developer_task: str
    is_satisfied: bool
    suggestions: List[str]
    parsed_config: Dict[str, Any]
    identified_files: Dict[str, Any]
    modification_plan: Dict[str, Any]
    generated_code: Dict[str, Any]

# ---------- Agents ---------------------
rephrase_agent = QueryRephraseAgent()
parser_agent = ParserAgent()
master_planner_agent = MasterPlannerAgent()
delta_analyzer_agent = DeltaAnalyzerAgent()
code_generator_agent = CodeGeneratorAgent()

# ---------- LangGraph Nodes ------------
async def rephrase_node(state: BotState) -> BotState:
    result = await rephrase_agent.rephrase_query(
        user_query=state["latest_query"],
        conversation_history=state["user_history"]
    )
    state["developer_task"] = result.get("developer_task", "")
    state["is_satisfied"] = result.get("is_satisfied", False)
    state["suggestions"] = result.get("suggestions", [])
    return state

async def parser_node(state: BotState) -> BotState:
    try:
        with open("examples/sample_config.json", "r") as f:
            config_data = json.load(f)
        parsed = await parser_agent.parse_config(config_data)
        if parsed:
            validated = parser_agent.validate_config(parsed)
            parsed["validation"] = validated
        state["parsed_config"] = parsed or {}
    except Exception as e:
        st.error(f"Failed to parse configuration: {e}")
    return state

async def identifier_node(state: BotState) -> BotState:
    try:
        identified = await master_planner_agent.identify_target_files(
            parsed_config=state["parsed_config"],
            project_path=settings.PROJECT_ROOT_PATH,
            user_question=state["developer_task"]
        )
        state["identified_files"] = identified or []
    except Exception as e:
        st.error(f"File identification failed: {e}")
        state["identified_files"] = []
    return state

async def delta_node(state: BotState) -> BotState:
    try:
        mod_plan = await delta_analyzer_agent.create_modification_plan(
            target_files=state["identified_files"],
            parsed_config=state["parsed_config"]
        )
        state["modification_plan"] = mod_plan
    except Exception as e:
        st.error(f"Delta analysis failed: {e}")
        state["modification_plan"] = {}
    return state

async def codegen_node(state: BotState) -> BotState:
    full_result = {
        "modified_files": [],
        "new_files": [],
        "errors": [],
        "warnings": []
    }

    files = state.get("modification_plan", {}).get("files_to_modify", [])

    for file_mod in files:
        await asyncio.sleep(10)  # Rate limit prevention

        single_plan = copy.deepcopy(state["modification_plan"])
        single_plan["files_to_modify"] = [file_mod]
        single_plan["execution_order"] = [file_mod["file_path"]]

        try:
            result = await code_generator_agent.generate_code_modifications(single_plan)
            if result:
                full_result["modified_files"].extend(result.get("modified_files", []))
                full_result["new_files"].extend(result.get("new_files", []))
                full_result["errors"].extend(result.get("errors", []))
                full_result["warnings"].extend(result.get("warnings", []))
        except Exception as e:
            full_result["errors"].append(f"{file_mod['file_path']}: {str(e)}")

        await asyncio.sleep(10)  # More buffer for token cooldown

    state["generated_code"] = full_result
    return state

# ---------- LangGraph Pipeline ----------
graph = StateGraph(BotState)
graph.set_entry_point("rephrase")
graph.add_node("rephrase", rephrase_node)
graph.add_node("parser", parser_node)
graph.add_node("identifier", identifier_node)
graph.add_node("delta", delta_node)
graph.add_node("codegen", codegen_node)
graph.add_conditional_edges("rephrase", lambda state: "parser" if state["is_satisfied"] else END)
graph.add_edge("parser", "identifier")
graph.add_edge("identifier", "delta")
graph.add_edge("delta", "codegen")
graph.add_edge("codegen", END)
final_graph = graph.compile()

# ---------- Streamlit UI ---------------
st.set_page_config(page_title="Async Dev Agent", layout="wide")
st.title("🤖 Async Dev Task → Config → Code Generator")

if "session_state" not in st.session_state:
    st.session_state.session_state = {
        "user_history": [],
        "latest_query": "",
        "developer_task": "",
        "is_satisfied": False,
        "suggestions": [],
        "parsed_config": {},
        "identified_files": [],
        "modification_plan": {},
        "generated_code": {}
    }

user_input = st.chat_input("Describe your development task...")

if user_input:
    st.session_state.session_state["latest_query"] = user_input
    st.session_state.session_state["user_history"].append(user_input)
    result = asyncio.run(final_graph.ainvoke(st.session_state.session_state))
    st.session_state.session_state.update(result)

# ---------- Output Display -------------
with st.chat_message("assistant"):
    if st.session_state.session_state["is_satisfied"]:
        st.success("✅ Task understood and processed.")
        st.markdown(f"**🧠 Developer Task:** `{st.session_state.session_state['developer_task']}`")

        st.subheader("📦 Parsed Configuration")
        st.json(st.session_state.session_state["parsed_config"])

        st.subheader("📁 Identified Files")
        st.json(st.session_state.session_state["identified_files"])

        st.subheader("📝 Modification Plan")
        st.json(st.session_state.session_state["modification_plan"])

        st.subheader("💻 Generated Code")
        for mod in st.session_state.session_state["generated_code"].get("modified_files", []):
            st.markdown(f"### `{mod['file_path']}`")
            st.code(mod.get("modified_content", ""), language="python")

    elif st.session_state.session_state["latest_query"]:
        st.warning("⚠️ Your query wasn't specific enough.")
        st.markdown("Suggestions:")
        for s in st.session_state.session_state["suggestions"]:
            st.markdown(f"- {s}")

if st.session_state.session_state["user_history"]:
    with st.expander("🗂️ Query History"):
        for i, query in enumerate(st.session_state.session_state["user_history"], 1):
            st.markdown(f"**{i}.** {query}")
