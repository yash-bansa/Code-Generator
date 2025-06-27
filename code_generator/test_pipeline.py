import streamlit as st
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from agents.QueryRephraseAgent import QueryRephraseAgent
from agents.parser_agent import ParserAgent
from agents.master_planner_agent import MasterPlannerAgent
from agents.delta_analyzer_agent import DeltaAnalyzerAgent
from agents.code_generator_agent import CodeGeneratorAgent  
from agents.code_validator_agent import CodeValidatorAgent
from config.settings import settings
import json
import sys
import time
from pathlib import Path
import copy

# Optional: Set path to root if needed
sys.path.append(str(Path(__file__).resolve().parents[1]))

# ----------- LangGraph State --------------
class BotState(TypedDict):
    user_history: List[str]
    latest_query: str
    developer_task: str
    is_satisfied: bool
    suggestions: List[str]
    parsed_config: Dict[str, Any]
    identified_files: Dict[str, Any]
    modification_plan: Dict[str, Any]
    generated_code: Dict[str, str]
    validation_result: Dict[str, Any]

# ---------- Agents ------------------------
rephrase_agent = QueryRephraseAgent()
parser_agent = ParserAgent()
master_planner_agent = MasterPlannerAgent()
delta_analyzer_agent = DeltaAnalyzerAgent()
code_generator_agent = CodeGeneratorAgent()  
validator_agent = CodeValidatorAgent()

# ---------- LangGraph Nodes ---------------
def rephrase_node(state: BotState) -> BotState:
    response = rephrase_agent.rephrase_query(
        state["latest_query"],
        state["user_history"]
    )
    if response:
        state["developer_task"] = response.get("developer_task", "")
        state["is_satisfied"] = response.get("is_satisfied", False)
        state["suggestions"] = response.get("suggestions", [])
    return state

def parser_node(state: BotState) -> BotState:
    try:
        with open("examples/sample_config.json", "r") as f:
            config_data = json.load(f)
    except Exception as e:
        st.error(f"Failed to load config: {e}")
        return state

    parsed = parser_agent.parse_config(config_data)
    if parsed:
        validated = parser_agent.validate_config(parsed)
        parsed["validation"] = validated
    state["parsed_config"] = parsed or {}
    return state

def identifier_node(state: BotState) -> BotState:
    result = master_planner_agent.identify_target_files(
        parsed_config=state["parsed_config"],
        project_path=settings.PROJECT_ROOT_PATH,
        user_question=state["developer_task"]
    )
    mod_plan = delta_analyzer_agent.create_modification_plan(result, state["parsed_config"])
    state["identified_files"] = result
    state["modification_plan"] = mod_plan
    return state

def codegen_node(state: BotState) -> BotState:
    full_result = {"modified_files": [], "new_files": [], "errors": [], "warnings": []}
    files = state["modification_plan"].get("files_to_modify", [])

    for file_mod in files:
        time.sleep(10)
        single_plan = copy.deepcopy(state["modification_plan"])
        single_plan["files_to_modify"] = [file_mod]
        single_plan["execution_order"] = [file_mod["file_path"]]

        try:
            result = code_generator_agent.generate_code_modifications(single_plan)
            if result:
                full_result["modified_files"].extend(result.get("modified_files", []))
                full_result["new_files"].extend(result.get("new_files", []))
                full_result["errors"].extend(result.get("errors", []))
                full_result["warnings"].extend(result.get("warnings", []))
        except Exception as e:
            full_result["errors"].append(f"{file_mod['file_path']}: {str(e)}")

        time.sleep(10)  # prevent rate limits

    state["generated_code"] = full_result
    return state

def validation_node(state: BotState) -> BotState:
    max_retries = 3
    validated = validator_agent.validate_code_changes(state["generated_code"].get("modified_files", []))
    state["validation_result"] = validated

    if validated.get("overall_status") == "passed":
        validator_agent.save_successful_validation_output(
            validated,
            state["generated_code"].get("modified_files", []),
            output_dir="output_new_1/generated_code"
        )
    else:
        for i in range(max_retries):
            retry_result = master_planner_agent.identify_target_files(
                parsed_config=state["parsed_config"],
                project_path=settings.PROJECT_ROOT_PATH,
                user_question=state["developer_task"]
            )
            retry_plan = delta_analyzer_agent.create_modification_plan(retry_result, state["parsed_config"])

            retry_generated = code_generator_agent.generate_code_modifications(retry_plan)
            retry_validated = validator_agent.validate_code_changes(retry_generated.get("modified_files", []))

            if retry_validated.get("overall_status") == "passed":
                validator_agent.save_successful_validation_output(
                    retry_validated,
                    retry_generated.get("modified_files", []),
                    output_dir="output_new_1/generated_code"
                )
                state["identified_files"] = retry_result
                state["modification_plan"] = retry_plan
                state["generated_code"] = retry_generated
                state["validation_result"] = retry_validated
                break

    return state

# ------------- Build LangGraph -------------
graph = StateGraph(BotState)
graph.add_node("rephrase", rephrase_node)
graph.add_node("parser", parser_node)
graph.add_node("identifier", identifier_node)
graph.add_node("codegen", codegen_node)
graph.add_node("validator", validation_node)

graph.set_entry_point("rephrase")

def condition(state: BotState) -> str:
    return "parser" if state["is_satisfied"] else END

graph.add_conditional_edges("rephrase", condition)
graph.add_edge("parser", "identifier")
graph.add_edge("identifier", "codegen")
graph.add_edge("codegen", "validator")
graph.add_edge("validator", END)

final_graph = graph.compile()

# -------------- Streamlit UI ----------------
st.set_page_config(page_title="💡 Dev Task to Code Generator", layout="wide")
st.title("🧐 Developer Task → Config → Code Generator")

if "session_state" not in st.session_state:
    st.session_state.session_state = {
        "user_history": [],
        "latest_query": "",
        "developer_task": "",
        "is_satisfied": False,
        "suggestions": [],
        "parsed_config": {},
        "identified_files": {},
        "modification_plan": {},
        "generated_code": {},
        "validation_result": {}
    }

user_input = st.chat_input("Describe your development task...")

if user_input:
    st.session_state.session_state["latest_query"] = user_input
    st.session_state.session_state["user_history"].append(user_input)
    result = final_graph.invoke(st.session_state.session_state)
    st.session_state.session_state.update(result)

# -------- Display Output ------------------
with st.chat_message("assistant"):
    if st.session_state.session_state["is_satisfied"]:
        st.success("✅ Developer task accepted and processed.")

        st.markdown(f"**🔩 Developer Task:** `{st.session_state.session_state['developer_task']}`")

        st.divider()
        st.subheader("📦 Parsed Configuration")
        st.json(st.session_state.session_state["parsed_config"])

        st.subheader("🔍 Identified Files to Modify")
        st.json(st.session_state.session_state["identified_files"])

        st.subheader("💪 Modification Plan")
        st.json(st.session_state.session_state["modification_plan"])

        st.subheader("💻 Generated Code Modifications")
        modified_files = st.session_state.session_state["generated_code"].get("modified_files", [])
        if not modified_files:
            st.info("No file modifications were generated.")
        else:
            for file in modified_files:
                st.markdown(f"### 📄 `{file['file_path']}`")
                st.caption(f"💪 {file.get('modifications_applied', 0)} modifications applied")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🔍 Original Content**")
                    st.code(file["original_content"], language="python")
                with col2:
                    st.markdown("**✅ Modified Content**")
                    st.code(file["modified_content"], language="python")

        st.divider()
        st.subheader("🧠 AI Validation Result")
        validation_result = st.session_state.session_state.get("validation_result", {})
        if not validation_result:
            st.info("Validation did not run.")
        else:
            if validation_result.get("overall_status") == "passed":
                st.success("🎉 Code validation passed!")
            else:
                st.error("❌ Code validation failed after retries.")
            st.json(validation_result)

    elif st.session_state.session_state["latest_query"]:
        st.warning("⚠️ Your query isn't clear enough yet.")
        st.write("Suggestions to improve your request:")
        for s in st.session_state.session_state["suggestions"]:
            st.markdown(f"- {s}")

# Show user history
if st.session_state.session_state["user_history"]:
    with st.expander("🗒️ Query History"):
        for i, q in enumerate(st.session_state.session_state["user_history"], 1):
            st.write(f"{i}. {q}")

