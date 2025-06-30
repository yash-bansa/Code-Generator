import streamlit as st
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
import asyncio
import json
import sys
import time
from pathlib import Path
import copy
import logging

# Import your agents
from agents.QueryRephraseAgent import QueryRephraseAgent
from agents.parser_agent import ParserAgent
from agents.master_planner_agent import MasterPlannerAgent
from agents.delta_analyzer_agent import DeltaAnalyzerAgent
from agents.code_generator_agent import CodeGeneratorAgent  
from agents.code_validator_agent import CodeValidatorAgent
from config.settings import settings

# Optional: Set path to root if needed
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------- LangGraph State --------------
class BotState(TypedDict):
    user_history: List[str]
    latest_query: str
    developer_task: str
    is_satisfied: bool
    suggestions: List[str]
    parsed_config: Dict[str, Any]
    identified_files: List[Dict[str, Any]]  # Fixed type
    modification_plan: Dict[str, Any]
    generated_code: Dict[str, Any]
    validation_result: Dict[str, Any]

# ---------- Agents ------------------------
rephrase_agent = QueryRephraseAgent()
parser_agent = ParserAgent()
master_planner_agent = MasterPlannerAgent()
delta_analyzer_agent = DeltaAnalyzerAgent()
code_generator_agent = CodeGeneratorAgent()  
validator_agent = CodeValidatorAgent()

# ---------- Async LangGraph Nodes ---------------
async def rephrase_node(state: BotState) -> BotState:
    """Async rephrase node with error handling"""
    try:
        logger.info("🔄 Processing query rephrase...")
        
        response = await rephrase_agent.rephrase_query(
            state["latest_query"],
            state["user_history"]
        )
        
        if response:
            state["developer_task"] = response.get("developer_task", "")
            state["is_satisfied"] = response.get("is_satisfied", False)
            state["suggestions"] = response.get("suggestions", [])
            logger.info(f"✅ Query rephrased. Satisfied: {state['is_satisfied']}")
        else:
            logger.warning("⚠️ Empty response from rephrase agent")
            state["is_satisfied"] = False
            state["suggestions"] = ["Please provide more specific details about your task."]
            
    except Exception as e:
        logger.error(f"❌ Rephrase node error: {e}")
        state["is_satisfied"] = False
        state["suggestions"] = [f"Error processing query: {str(e)}"]
    
    return state

async def parser_node(state: BotState) -> BotState:
    """Async parser node with multiple config fallbacks"""
    try:
        logger.info("🔄 Loading and parsing configuration...")
        
        # Try multiple config paths
        config_paths = [
            "examples/sample_config.json",
            "config/default_config.json",
            "sample_config.json"
        ]
        
        config_data = None
        for config_path in config_paths:
            try:
                if Path(config_path).exists():
                    with open(config_path, "r") as f:
                        config_data = json.load(f)
                    logger.info(f"✅ Loaded config from {config_path}")
                    break
            except Exception as e:
                logger.warning(f"Failed to load {config_path}: {e}")
                continue
        
        if not config_data:
            # Create minimal default config
            config_data = {
                "data_sources": [],
                "transformations": [],
                "outputs": [],
                "processing_config": {"batch_size": 1000}
            }
            logger.warning("⚠️ Using default minimal configuration")
        
        parsed = await parser_agent.parse_config(config_data)
        if parsed:
            validated = parser_agent.validate_config(parsed)
            parsed["validation"] = validated
            logger.info("✅ Configuration parsed and validated")
        else:
            parsed = config_data
            logger.warning("⚠️ Parser failed, using original config")
        
        state["parsed_config"] = parsed
        
    except Exception as e:
        logger.error(f"❌ Parser node error: {e}")
        state["parsed_config"] = {
            "data_sources": [],
            "transformations": [],
            "outputs": [],
            "error": f"Configuration parsing failed: {str(e)}"
        }
    
    return state

async def identifier_node(state: BotState) -> BotState:
    """Async identifier node with error handling"""
    try:
        logger.info("🔄 Identifying target files...")
        
        result = await master_planner_agent.identify_target_files(
            parsed_config=state["parsed_config"],
            project_path=settings.PROJECT_ROOT_PATH,
            user_question=state["developer_task"]
        )
        
        logger.info(f"✅ Identified {len(result)} target files")
        
        mod_plan = await delta_analyzer_agent.create_modification_plan(
            result, 
            state["parsed_config"]
        )
        
        state["identified_files"] = result
        state["modification_plan"] = mod_plan
        
        logger.info("✅ Modification plan created")
        
    except Exception as e:
        logger.error(f"❌ Identifier node error: {e}")
        state["identified_files"] = []
        state["modification_plan"] = {"files_to_modify": [], "errors": [str(e)]}
    
    return state

async def codegen_node(state: BotState) -> BotState:
    """Async code generation node with progress tracking"""
    try:
        logger.info("🔄 Starting code generation...")
        
        full_result = {
            "modified_files": [], 
            "new_files": [], 
            "errors": [], 
            "warnings": [],
            "processing_summary": {
                "total_files": 0,
                "successful": 0,
                "failed": 0
            }
        }
        
        files = state["modification_plan"].get("files_to_modify", [])
        
        if not files:
            logger.warning("⚠️ No files to modify")
            full_result["warnings"].append("No files identified for modification")
            state["generated_code"] = full_result
            return state
        
        full_result["processing_summary"]["total_files"] = len(files)
        
        # Create progress indicator
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        for i, file_mod in enumerate(files):
            try:
                file_path = file_mod.get("file_path", "unknown")
                file_name = Path(file_path).name
                
                logger.info(f"🔄 Processing file {i+1}/{len(files)}: {file_name}")
                
                # Update progress UI
                progress = (i + 1) / len(files)
                progress_placeholder.progress(progress)
                status_placeholder.text(f"Processing {file_name} ({i+1}/{len(files)})")
                
                # Create single file modification plan
                single_plan = copy.deepcopy(state["modification_plan"])
                single_plan["files_to_modify"] = [file_mod]
                single_plan["execution_order"] = [file_path]
                
                # Generate code with timeout
                try:
                    result = await asyncio.wait_for(
                        code_generator_agent.generate_code_modifications(single_plan),
                        timeout=120.0  # 2 minute timeout per file
                    )
                    
                    if result:
                        full_result["modified_files"].extend(result.get("modified_files", []))
                        full_result["new_files"].extend(result.get("new_files", []))
                        full_result["errors"].extend(result.get("errors", []))
                        full_result["warnings"].extend(result.get("warnings", []))
                        full_result["processing_summary"]["successful"] += 1
                        logger.info(f"✅ Successfully processed {file_name}")
                    else:
                        error_msg = f"Empty result for {file_path}"
                        full_result["errors"].append(error_msg)
                        full_result["processing_summary"]["failed"] += 1
                        logger.error(error_msg)
                        
                except asyncio.TimeoutError:
                    error_msg = f"Timeout processing {file_path}"
                    full_result["errors"].append(error_msg)
                    full_result["processing_summary"]["failed"] += 1
                    logger.error(error_msg)
                    
            except Exception as e:
                error_msg = f"{file_mod.get('file_path', 'unknown')}: {str(e)}"
                full_result["errors"].append(error_msg)
                full_result["processing_summary"]["failed"] += 1
                logger.error(f"❌ File processing error: {error_msg}")
            
            # Brief pause to prevent overwhelming the system
            await asyncio.sleep(2)
        
        # Clean up progress indicators
        progress_placeholder.empty()
        status_placeholder.empty()
        
        logger.info(f"✅ Code generation complete. Success: {full_result['processing_summary']['successful']}, Failed: {full_result['processing_summary']['failed']}")
        
        state["generated_code"] = full_result
        
    except Exception as e:
        logger.error(f"❌ Codegen node error: {e}")
        state["generated_code"] = {
            "modified_files": [],
            "errors": [f"Code generation failed: {str(e)}"]
        }
    
    return state

async def validation_node(state: BotState) -> BotState:
    """Async validation node with intelligent retry"""
    try:
        logger.info("🔄 Starting validation...")
        
        modified_files = state["generated_code"].get("modified_files", [])
        
        if not modified_files:
            logger.warning("⚠️ No modified files to validate")
            state["validation_result"] = {
                "overall_status": "skipped",
                "message": "No files to validate"
            }
            return state
        
        # Initial validation
        validated = await validator_agent.validate_code_changes(modified_files)
        state["validation_result"] = validated
        
        if validated.get("overall_status") == "passed":
            logger.info("✅ Validation passed on first attempt")
            
            # Save successful results
            try:
                await save_successful_results(
                    validated,
                    modified_files,
                    output_dir="output_new_1/generated_code"
                )
                st.success("🎉 Code generated and saved successfully!")
                
            except Exception as e:
                logger.error(f"Failed to save results: {e}")
                st.warning(f"⚠️ Validation passed but failed to save: {e}")
        
        else:
            logger.warning(f"⚠️ Initial validation failed: {validated.get('overall_status')}")
            
            # Smart retry with different strategies
            max_retries = 2
            retry_strategies = ["conservative", "focused"]
            
            for retry_num in range(max_retries):
                try:
                    logger.info(f"🔄 Retry attempt {retry_num + 1}/{max_retries}")
                    
                    retry_result = await intelligent_retry(
                        state,
                        strategy=retry_strategies[retry_num],
                        validation_errors=validated.get("errors_found", [])
                    )
                    
                    if retry_result and retry_result.get("overall_status") == "passed":
                        logger.info(f"✅ Retry {retry_num + 1} succeeded")
                        
                        # Update state with successful retry
                        state.update(retry_result["state_updates"])
                        state["validation_result"] = retry_result["validation"]
                        
                        await save_successful_results(
                            retry_result["validation"],
                            retry_result["modified_files"],
                            output_dir="output_new_1/generated_code"
                        )
                        
                        st.success(f"🎉 Succeeded on retry {retry_num + 1}!")
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Retry {retry_num + 1} failed: {e}")
                    continue
            
            else:
                logger.error("❌ All retry attempts failed")
                st.error("❌ Code generation failed after multiple attempts")
    
    except Exception as e:
        logger.error(f"❌ Validation node error: {e}")
        state["validation_result"] = {
            "overall_status": "error",
            "error": str(e)
        }
    
    return state

# ---------- Helper Functions ---------------
async def intelligent_retry(state: BotState, strategy: str, validation_errors: List[str]) -> Dict[str, Any]:
    """Intelligent retry with different strategies"""
    try:
        if strategy == "conservative":
            retry_files = await master_planner_agent.identify_target_files(
                parsed_config=state["parsed_config"],
                project_path=settings.PROJECT_ROOT_PATH,
                user_question=f"CONSERVATIVE: {state['developer_task']}"
            )
        elif strategy == "focused":
            original_files = state.get("identified_files", [])
            retry_files = [f for f in original_files if f.get("priority") == "high"]
        
        if not retry_files:
            return None
        
        retry_plan = await delta_analyzer_agent.create_modification_plan(
            retry_files, state["parsed_config"]
        )
        
        retry_generated = await code_generator_agent.generate_code_modifications(retry_plan)
        
        retry_validated = await validator_agent.validate_code_changes(
            retry_generated.get("modified_files", [])
        )
        
        if retry_validated.get("overall_status") == "passed":
            return {
                "overall_status": "passed",
                "validation": retry_validated,
                "modified_files": retry_generated.get("modified_files", []),
                "state_updates": {
                    "identified_files": retry_files,
                    "modification_plan": retry_plan,
                    "generated_code": retry_generated
                }
            }
        
    except Exception as e:
        logger.error(f"❌ Intelligent retry failed: {e}")
    
    return None

async def save_successful_results(validation_result: Dict[str, Any], modified_files: List[Dict[str, Any]], output_dir: str):
    """Save successful results with proper organization"""
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save validation report
        with open(output_path / "validation_report.json", "w") as f:
            json.dump(validation_result, f, indent=2)
        
        # Save modified files
        for file_data in modified_files:
            file_path = file_data.get("file_path", "")
            if file_path:
                relative_path = Path(file_path).name
                output_file = output_path / f"modified_{relative_path}"
                
                with open(output_file, "w") as f:
                    f.write(file_data.get("modified_content", ""))
        
        logger.info(f"✅ Results saved to {output_dir}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save results: {e}")
        raise

# ------------- Build Async LangGraph -------------
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
st.set_page_config(
    page_title="💡 AI Code Generator", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.success-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    margin: 1rem 0;
}
.error-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI-Powered Code Generator")
st.markdown("Transform your development ideas into working code!")

# Initialize session state
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
        "generated_code": {},
        "validation_result": {}
    }

# Sidebar for status and settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Project path
    project_path = st.text_input(
        "Project Root Path", 
        value=str(settings.PROJECT_ROOT_PATH),
        help="Path to your project directory"
    )
    
    # Status indicator
    if st.session_state.session_state.get("latest_query"):
        st.header("📊 Processing Status")
        
        status_steps = [
            ("Query Processing", st.session_state.session_state.get("is_satisfied", False)),
            ("Config Parsing", bool(st.session_state.session_state.get("parsed_config"))),
            ("File Identification", bool(st.session_state.session_state.get("identified_files"))),
            ("Code Generation", bool(st.session_state.session_state.get("generated_code"))),
            ("Validation", bool(st.session_state.session_state.get("validation_result")))
        ]
        
        for step_name, completed in status_steps:
            icon = "✅" if completed else "⏳"
            st.markdown(f"{icon} {step_name}")

# Main input area
st.header("💬 Describe Your Development Task")

# Example prompts
with st.expander("💡 Example Prompts"):
    examples = [
        "Create an ETL pipeline to extract data from MySQL and generate Excel reports",
        "Build a REST API to manage user authentication and data access",
        "Develop a data analysis script to process CSV files and create visualizations",
        "Create a web scraper to collect product information from e-commerce sites"
    ]
    
    for example in examples:
        if st.button(example, key=f"example_{hash(example)}"):
            st.session_state.session_state["latest_query"] = example
            st.rerun()

# Main chat input
user_input = st.chat_input("Example: Create an ETL pipeline to process customer data...")

# Process user input
if user_input:
    st.session_state.session_state["latest_query"] = user_input
    st.session_state.session_state["user_history"].append(user_input)
    
    # Show processing indicator
    with st.spinner("🔄 Processing your request..."):
        try:
            # Run the async graph
            result = asyncio.run(final_graph.ainvoke(st.session_state.session_state))
            st.session_state.session_state.update(result)
        except Exception as e:
            st.error(f"❌ Processing failed: {str(e)}")
            logger.error(f"❌ Graph execution failed: {e}")

# -------- Display Output ------------------
with st.chat_message("assistant"):
    if st.session_state.session_state["is_satisfied"]:
        st.success("✅ Developer task accepted and processed.")
        st.markdown(f"**🔩 Developer Task:** `{st.session_state.session_state['developer_task']}`")
        
        # Configuration section
        with st.expander("📦 Parsed Configuration", expanded=False):
            st.json(st.session_state.session_state["parsed_config"])
        
        # Identified files section
        with st.expander("🔍 Identified Files to Modify", expanded=False):
            identified_files = st.session_state.session_state["identified_files"]
            if identified_files:
                st.info(f"Found {len(identified_files)} files to modify")
                for file_info in identified_files:
                    st.markdown(f"- **{file_info.get('file_path', 'Unknown')}** (Priority: {file_info.get('priority', 'medium')})")
            st.json(identified_files)
        
        # Modification plan section
        with st.expander("💪 Modification Plan", expanded=False):
            st.json(st.session_state.session_state["modification_plan"])
        
        # Generated code section
        st.subheader("💻 Generated Code Modifications")
        modified_files = st.session_state.session_state["generated_code"].get("modified_files", [])
        
        if not modified_files:
            st.info("No file modifications were generated.")
        else:
            st.success(f"✅ Generated modifications for {len(modified_files)} files")
            
            for i, file in enumerate(modified_files):
                with st.expander(f"📄 {file['file_path']}", expanded=i == 0):
                    st.caption(f"💪 {file.get('modifications_applied', 0)} modifications applied")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**🔍 Original Content**")
                        st.code(file["original_content"][:2000] + "..." if len(file["original_content"]) > 2000 else file["original_content"], 
                               language="python", line_numbers=True)
                    
                    with col2:
                        st.markdown("**✅ Modified Content**")
                        st.code(file["modified_content"][:2000] + "..." if len(file["modified_content"]) > 2000 else file["modified_content"], 
                               language="python", line_numbers=True)
        
        # Validation results
        st.subheader("🧠 AI Validation Result")
        validation_result = st.session_state.session_state.get("validation_result", {})
        
        if not validation_result:
            st.info("Validation did not run.")
        else:
            status = validation_result.get("overall_status", "unknown")
            
            if status == "passed":
                st.success("🎉 Code validation passed!")
            elif status == "skipped":
                st.info("⏭️ Validation was skipped")
            else:
                st.error("❌ Code validation failed")
            
            # Show validation details in expander
            with st.expander("🔍 Validation Details", expanded=status != "passed"):
                st.json(validation_result)
                
                # Show errors if any
                errors = validation_result.get("errors_found", [])
                if errors:
                    st.error("**Errors Found:**")
                    for error in errors:
                        st.markdown(f"- {error}")
                
                # Show warnings if any
                warnings = validation_result.get("warnings", [])
                if warnings:
                    st.warning("**Warnings:**")
                    for warning in warnings:
                        st.markdown(f"- {warning}")
    
    elif st.session_state.session_state["latest_query"]:
        st.warning("⚠️ Your query isn't clear enough yet.")
        st.write("**Suggestions to improve your request:**")
        for s in st.session_state.session_state["suggestions"]:
            st.markdown(f"- {s}")

# Show user history
if st.session_state.session_state["user_history"]:
    with st.expander("🗒️ Query History"):
        for i, q in enumerate(st.session_state.session_state["user_history"], 1):
            st.write(f"**{i}.** {q}")

# Add a reset button
if st.button("🔄 Reset Session"):
    st.session_state.session_state = {
        "user_history": [],
        "latest_query": "",
        "developer_task": "",
        "is_satisfied": False,
        "suggestions": [],
        "parsed_config": {},
        "identified_files": [],
        "modification_plan": {},
        "generated_code": {},
        "validation_result": {}
    }
    st.success("✅ Session reset!")
    st.rerun()