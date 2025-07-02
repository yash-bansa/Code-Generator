import streamlit as st
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any, Optional
import asyncio
import json
import sys
import time
from pathlib import Path
import copy
import logging

# Import your existing agents
from agents.parser_agent import ParserAgent
from agents.master_planner_agent import MasterPlannerAgent
from agents.delta_analyzer_agent import DeltaAnalyzerAgent
from agents.code_generator_agent import CodeGeneratorAgent  
from agents.code_validator_agent import CodeValidatorAgent
from config.agents_io import CommunicationInput,CommunicationOutput,QueryEnhancerInput,QueryEnhancerOutput
# Import new communication agents
from agents.communication_agent import CommunicationAgent
from agents.QueryRephraseAgent import QueryRephraserAgent

from config.settings import settings

# Optional: Set path to root if needed
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------- Progress Manager Class ---------------
class ProgressManager:
    """Manages Streamlit progress indicators safely"""
    
    def __init__(self):
        self.progress_bar = None
        self.status_text = None
        self.container = None
    
    def create_progress_ui(self):
        """Create progress UI elements"""
        if self.container is None:
            self.container = st.container()
        
        with self.container:
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()
    
    def update_progress(self, value: float, text: str = ""):
        """Update progress bar and text"""
        try:
            if self.progress_bar is not None:
                self.progress_bar.progress(value)
            if self.status_text is not None and text:
                self.status_text.text(text)
        except Exception as e:
            logger.warning(f"Progress update failed: {e}")
    
    def cleanup(self):
        """Clean up progress UI elements"""
        try:
            if self.progress_bar is not None:
                self.progress_bar.empty()
            if self.status_text is not None:
                self.status_text.empty()
            if self.container is not None:
                self.container.empty()
        except Exception as e:
            logger.warning(f"Progress cleanup failed: {e}")
        finally:
            self.progress_bar = None
            self.status_text = None
            self.container = None

# Global progress manager
progress_manager = ProgressManager()

# ----------- Enhanced LangGraph State --------------
class BotState(TypedDict):
    # Original fields
    user_history: List[str]
    latest_query: str
    developer_task: str
    is_satisfied: bool
    suggestions: List[str]
    parsed_config: Dict[str, Any]
    identified_files: List[Dict[str, Any]]
    modification_plan: Dict[str, Any]
    generated_code: Dict[str, Any]
    validation_result: Dict[str, Any]
    
    # New communication fields
    conversation_active: bool
    communication_round: int
    core_intent: str
    context_notes: str
    user_message: str
    needs_clarification: bool

# ---------- Enhanced Agents ------------------------
# Original agents
parser_agent = ParserAgent()
master_planner_agent = MasterPlannerAgent()
delta_analyzer_agent = DeltaAnalyzerAgent()
code_generator_agent = CodeGeneratorAgent()  
validator_agent = CodeValidatorAgent()

# New communication agents
communication_agent = CommunicationAgent()
query_rephraser_agent = QueryRephraserAgent()

# ---------- New Communication Orchestration Nodes ---------------
async def communication_node(state: BotState) -> BotState:
    """Handle user communication and intent extraction"""
    try:
        logger.info("🗣️ Processing user communication...")
        progress_manager.update_progress(0.1, "🗣️ Processing user communication...")

        comm_result: CommunicationOutput = await communication_agent.extract_intent(
            CommunicationInput(
                user_query=state["latest_query"],
                conversation_history=state["user_history"][:-1] if len(state["user_history"]) > 1 else []
            )
        )

        state["core_intent"] = comm_result.core_intent
        state["context_notes"] = comm_result.context_notes
        state["communication_round"] = state.get("communication_round", 0) + 1

        if not comm_result.success:
            logger.warning(f"[Fallback] CommunicationAgent used fallback: {comm_result.message}")
            progress_manager.update_progress(0.2, "⚠️ Used fallback communication")

        else:
            logger.info(f"✅ Communication processed. Intent: {comm_result.core_intent}")
            progress_manager.update_progress(0.2, "✅ Communication processed")

        return state

    except Exception as e:
        logger.error(f"❌ Communication node error: {e}")
        state["core_intent"] = state["latest_query"]
        state["context_notes"] = f"Error in communication processing: {str(e)}"
        progress_manager.update_progress(0.2, "⚠️ Communication processing error")
        return state


async def query_enhancement_node(state: BotState) -> BotState:
    """Enhance and validate query completeness"""
    try:
        logger.info("🔧 Enhancing query with rephraser agent...")
        progress_manager.update_progress(0.3, "🔧 Enhancing query...")

        # ✅ Correct way to call the enhance_query method
        enhancer_input = QueryEnhancerInput(
            core_intent=state["core_intent"],
            context_notes=state["context_notes"]
        )
        enhancer_result: QueryEnhancerOutput = await query_rephraser_agent.enhance_query(enhancer_input)

        # Update state with enhancement results
        state["developer_task"] = enhancer_result.developer_task
        state["is_satisfied"] = enhancer_result.is_satisfied
        state["suggestions"] = enhancer_result.suggestions
        state["needs_clarification"] = not enhancer_result.is_satisfied

        if not enhancer_result.success:
            logger.warning(f"[Fallback] QueryEnhancerAgent returned fallback: {enhancer_result.message}")

        if enhancer_result.is_satisfied:
            state["user_message"] = f"Perfect! I understand you want to: **{enhancer_result.developer_task}**\n\nProceeding with code generation..."
            logger.info("✅ Query enhancement complete - satisfied")
            progress_manager.update_progress(0.4, "✅ Query enhanced - proceeding")
        else:
            message_parts = [
                f"I understand you want to: **{enhancer_result.developer_task}**",
                "",
                "To provide the best solution, I need more information:"
            ]
            for i, suggestion in enumerate(enhancer_result.suggestions, 1):
                message_parts.append(f"{i}. {suggestion}")
            message_parts.append("\nCould you please provide these details? 🤔")
            state["user_message"] = "\n".join(message_parts)
            logger.info("⚠️ Query enhancement complete - needs clarification")
            progress_manager.update_progress(0.4, "⚠️ Need more information")

        return state

    except Exception as e:
        logger.error(f"❌ Query enhancement node error: {e}")
        state["is_satisfied"] = False
        state["suggestions"] = [f"Error processing query: {str(e)}"]
        state["user_message"] = "I encountered an error processing your request. Could you please try again?"
        progress_manager.update_progress(0.4, "❌ Query enhancement error")
        return state


# ---------- Original Nodes (Enhanced with Progress) ---------------
async def parser_node(state: BotState) -> BotState:
    """Enhanced parser node with better feedback"""
    try:
        logger.info("🔄 Loading and parsing configuration...")
        progress_manager.update_progress(0.5, "📦 Loading configuration...")
        
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
        
        progress_manager.update_progress(0.55, "🔧 Parsing configuration...")
        
        parsed = await parser_agent.parse_config(config_data)
        if parsed:
            validated = parser_agent.validate_config(parsed)
            parsed["validation"] = validated
            logger.info("✅ Configuration parsed and validated")
        else:
            parsed = config_data
            logger.warning("⚠️ Parser failed, using original config")
        
        state["parsed_config"] = parsed
        progress_manager.update_progress(0.6, "✅ Configuration ready")
        
    except Exception as e:
        logger.error(f"❌ Parser node error: {e}")
        state["parsed_config"] = {
            "data_sources": [],
            "transformations": [],
            "outputs": [],
            "error": f"Configuration parsing failed: {str(e)}"
        }
        progress_manager.update_progress(0.6, "❌ Configuration error")
    
    return state

async def identifier_node(state: BotState) -> BotState:
    """Enhanced identifier node with progress tracking"""
    try:
        logger.info("🔄 Identifying target files...")
        progress_manager.update_progress(0.65, "🔍 Identifying files to modify...")
        
        result = await master_planner_agent.identify_target_files(
            parsed_config=state["parsed_config"],
            project_path=settings.PROJECT_ROOT_PATH,
            user_question=state["developer_task"]
        )
        
        logger.info(f"✅ Identified {len(result)} target files")
        progress_manager.update_progress(0.7, f"✅ Found {len(result)} files")
        
        progress_manager.update_progress(0.72, "📋 Creating modification plan...")
        mod_plan = await delta_analyzer_agent.create_modification_plan(
            result, 
            state["parsed_config"]
        )
        
        state["identified_files"] = result
        state["modification_plan"] = mod_plan
        
        logger.info("✅ Modification plan created")
        progress_manager.update_progress(0.75, "✅ Modification plan ready")
        
    except Exception as e:
        logger.error(f"❌ Identifier node error: {e}")
        state["identified_files"] = []
        state["modification_plan"] = {"files_to_modify": [], "errors": [str(e)]}
        progress_manager.update_progress(0.75, "❌ File identification error")
    
    return state

async def codegen_node(state: BotState) -> BotState:
    """Enhanced code generation node with better progress tracking"""
    try:
        logger.info("🔄 Starting code generation...")
        progress_manager.update_progress(0.8, "💻 Starting code generation...")
        
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
            progress_manager.update_progress(0.9, "⚠️ No files to modify")
            return state
        
        full_result["processing_summary"]["total_files"] = len(files)
        
        for i, file_mod in enumerate(files):
            try:
                file_path = file_mod.get("file_path", "unknown")
                file_name = Path(file_path).name
                
                logger.info(f"🔄 Processing file {i+1}/{len(files)}: {file_name}")
                
                # Update progress
                file_progress = 0.8 + (0.1 * (i + 1) / len(files))
                progress_manager.update_progress(
                    file_progress, 
                    f"💻 Generating code for {file_name} ({i+1}/{len(files)})"
                )
                
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
            await asyncio.sleep(1)
        
        logger.info(f"✅ Code generation complete. Success: {full_result['processing_summary']['successful']}, Failed: {full_result['processing_summary']['failed']}")
        progress_manager.update_progress(0.9, "✅ Code generation complete")
        
        state["generated_code"] = full_result
        
    except Exception as e:
        logger.error(f"❌ Codegen node error: {e}")
        state["generated_code"] = {
            "modified_files": [],
            "errors": [f"Code generation failed: {str(e)}"]
        }
        progress_manager.update_progress(0.9, "❌ Code generation error")
    
    return state

async def validation_node(state: BotState) -> BotState:
    """Enhanced validation node with progress feedback"""
    try:
        logger.info("🔄 Starting validation...")
        progress_manager.update_progress(0.95, "🧠 Validating generated code...")
        
        modified_files = state["generated_code"].get("modified_files", [])
        
        if not modified_files:
            logger.warning("⚠️ No modified files to validate")
            state["validation_result"] = {
                "overall_status": "skipped",
                "message": "No files to validate"
            }
            progress_manager.update_progress(1.0, "⏭️ Validation skipped")
            return state
        
        # Initial validation
        validated = await validator_agent.validate_code_changes(modified_files)
        state["validation_result"] = validated
        
        if validated.get("overall_status") == "passed":
            logger.info("✅ Validation passed on first attempt")
            progress_manager.update_progress(1.0, "✅ Validation passed!")
            
            # Save successful results
            try:
                await save_successful_results(
                    validated,
                    modified_files,
                    output_dir="output_new_1/generated_code"
                )
                
            except Exception as e:
                logger.error(f"Failed to save results: {e}")
        
        else:
            logger.warning(f"⚠️ Initial validation failed: {validated.get('overall_status')}")
            progress_manager.update_progress(1.0, "⚠️ Validation issues found")
    
    except Exception as e:
        logger.error(f"❌ Validation node error: {e}")
        state["validation_result"] = {
            "overall_status": "error",
            "error": str(e)
        }
        progress_manager.update_progress(1.0, "❌ Validation error")
    
    return state

# ---------- Helper Functions ---------------
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

# ------------- Build Enhanced LangGraph -------------
graph = StateGraph(BotState)

# Add all nodes
graph.add_node("communication", communication_node)
graph.add_node("query_enhancement", query_enhancement_node)
graph.add_node("parser", parser_node)
graph.add_node("identifier", identifier_node)
graph.add_node("codegen", codegen_node)
graph.add_node("validator", validation_node)

# Set entry point to communication node
graph.set_entry_point("communication")

# Define conditional routing
def communication_condition(state: BotState) -> str:
    """Route based on communication results"""
    return "query_enhancement"

def enhancement_condition(state: BotState) -> str:
    """Route based on query enhancement results"""
    return "parser" if state["is_satisfied"] else END

# Add edges
graph.add_edge("communication", "query_enhancement")
graph.add_conditional_edges("query_enhancement", enhancement_condition)
graph.add_edge("parser", "identifier")
graph.add_edge("identifier", "codegen")
graph.add_edge("codegen", "validator")
graph.add_edge("validator", END)

final_graph = graph.compile()

# -------------- Enhanced Streamlit UI ----------------
st.set_page_config(
    page_title="💡 AI Code Generator with Smart Communication", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS
st.markdown("""
<style>
.conversation-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    margin: 1rem 0;
}
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
.communication-status {
    padding: 0.5rem;
    border-radius: 0.25rem;
    background-color: #e2e3e5;
    border-left: 4px solid #6c757d;
    margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI-Powered Code Generator with Smart Communication")
st.markdown("Intelligent conversation-driven code generation!")

# Initialize enhanced session state
if "session_state" not in st.session_state:
    st.session_state.session_state = {
        # Original fields
        "user_history": [],
        "latest_query": "",
        "developer_task": "",
        "is_satisfied": False,
        "suggestions": [],
        "parsed_config": {},
        "identified_files": [],
        "modification_plan": {},
        "generated_code": {},
        "validation_result": {},
        
        # New communication fields
        "conversation_active": False,
        "communication_round": 0,
        "core_intent": "",
        "context_notes": "",
        "user_message": "",
        "needs_clarification": False
    }

# Enhanced sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Project path
    project_path = st.text_input(
        "Project Root Path", 
        value=str(settings.PROJECT_ROOT_PATH),
        help="Path to your project directory"
    )
    
    # Communication status
    st.header("💬 Communication Status")
    
    if st.session_state.session_state.get("communication_round", 0) > 0:
        st.markdown(f"**Round:** {st.session_state.session_state['communication_round']}")
        
        if st.session_state.session_state.get("core_intent"):
            st.markdown(f"**Intent:** {st.session_state.session_state['core_intent'][:50]}...")
        
        if st.session_state.session_state.get("needs_clarification"):
            st.warning("⚠️ Needs Clarification")
        else:
            st.success("✅ Requirements Clear")
    
    # Processing status
    if st.session_state.session_state.get("latest_query"):
        st.header("📊 Processing Status")
        
        status_steps = [
            ("Communication", st.session_state.session_state.get("communication_round", 0) > 0),
            ("Query Enhancement", st.session_state.session_state.get("is_satisfied", False)),
            ("Config Parsing", bool(st.session_state.session_state.get("parsed_config"))),
            ("File Identification", bool(st.session_state.session_state.get("identified_files"))),
            ("Code Generation", bool(st.session_state.session_state.get("generated_code"))),
            ("Validation", bool(st.session_state.session_state.get("validation_result")))
        ]
        
        for step_name, completed in status_steps:
            icon = "✅" if completed else "⏳"
            st.markdown(f"{icon} {step_name}")

# Main conversation area
st.header("💬 Intelligent Conversation")

# Enhanced example prompts
with st.expander("💡 Example Prompts"):
    examples = [
        "I need help with data processing",
        "Create reports from my database",
        "Build an API for user management",
        "Process CSV files and create visualizations",
        "I want to automate my daily data tasks"
    ]
    
    col1, col2 = st.columns(2)
    
    for i, example in enumerate(examples):
        target_col = col1 if i % 2 == 0 else col2
        with target_col:
            if st.button(example, key=f"example_{hash(example)}", use_container_width=True):
                st.session_state.session_state["latest_query"] = example
                st.rerun()

# Conversation display
if st.session_state.session_state.get("user_message"):
    st.markdown("### 🤖 Assistant Response")
    st.markdown(f'<div class="conversation-box">{st.session_state.session_state["user_message"]}</div>', 
                unsafe_allow_html=True)

# Main chat input
user_input = st.chat_input("Describe what you want to build, or answer the questions above...")

# Process user input
if user_input:
    st.session_state.session_state["latest_query"] = user_input
    st.session_state.session_state["user_history"].append(user_input)
    
    # Show processing indicator with spinner
    with st.spinner("🔄 Processing your request..."):
        try:
            # Create progress UI
            progress_manager.create_progress_ui()
            
            # Run the enhanced async graph
            result = asyncio.run(final_graph.ainvoke(st.session_state.session_state))
            st.session_state.session_state.update(result)
            
            # Clean up progress UI
            progress_manager.cleanup()
            
        except Exception as e:
            st.error(f"❌ Processing failed: {str(e)}")
            logger.error(f"❌ Graph execution failed: {e}")
            progress_manager.cleanup()
        
        # Rerun to show updated state
        st.rerun()

# Enhanced output display
if st.session_state.session_state.get("latest_query"):
    
    # Show conversation status
    if st.session_state.session_state.get("needs_clarification"):
        st.warning("⚠️ **More information needed to proceed**")
        
        if st.session_state.session_state.get("suggestions"):
            st.markdown("**Please provide:**")
            for suggestion in st.session_state.session_state["suggestions"]:
                st.markdown(f"• {suggestion}")
    
    elif st.session_state.session_state.get("is_satisfied"):
        st.success("✅ **Requirements understood - Code generation complete**")
        
        # Show the rest of the processing results
        st.markdown(f"**🎯 Developer Task:** `{st.session_state.session_state['developer_task']}`")
        
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
        if st.session_state.session_state.get("generated_code"):
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
        if st.session_state.session_state.get("validation_result"):
            st.subheader("🧠 AI Validation Result")
            validation_result = st.session_state.session_state["validation_result"]
            
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

# Enhanced conversation history
if st.session_state.session_state["user_history"]:
    with st.expander("🗒️ Conversation History", expanded=False):
        for i, q in enumerate(st.session_state.session_state["user_history"], 1):
            st.markdown(f"**{i}.** {q}")
        
        # Show communication insights
        if st.session_state.session_state.get("core_intent"):
            st.markdown("---")
            st.markdown(f"**🎯 Extracted Intent:** {st.session_state.session_state['core_intent']}")
        
        if st.session_state.session_state.get("context_notes"):
            st.markdown(f"**📝 Context Notes:** {st.session_state.session_state['context_notes']}")

# Enhanced control buttons
col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 Reset Session", use_container_width=True):
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
            "validation_result": {},
            "conversation_active": False,
            "communication_round": 0,
            "core_intent": "",
            "context_notes": "",
            "user_message": "",
            "needs_clarification": False
        }
        # Clean up progress manager
        progress_manager.cleanup()
        st.success("✅ Session reset!")
        st.rerun()

with col2:
    if st.button("💾 Export Session", use_container_width=True):
        # Export session data
        export_data = {
            "timestamp": time.time(),
            "conversation_history": st.session_state.session_state["user_history"],
            "final_developer_task": st.session_state.session_state.get("developer_task"),
            "communication_rounds": st.session_state.session_state.get("communication_round", 0),
            "was_satisfied": st.session_state.session_state.get("is_satisfied", False)
        }
        
        st.download_button(
            label="📥 Download Session Data",
            data=json.dumps(export_data, indent=2),
            file_name=f"ai_code_session_{int(time.time())}.json",
            mime="application/json",
            use_container_width=True
        )