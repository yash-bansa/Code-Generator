import json
import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from pathlib import Path
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
# from langgraph.prebuilt import ToolExecutor


from agents.parser_agent import ParserAgent
from agents.code_identifier_agent import CodeIdentifierAgent
from agents.code_generator_agent import CodeGeneratorAgent
from agents.code_validator_agent import CodeValidatorAgent
from utils.file_handler import FileHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State object for the workflow"""
    # Input data
    config_data: Dict[str, Any]
    project_path: str
    
    # Parsing results
    parsed_config: Optional[Dict[str, Any]]
    parsing_errors: List[str]
    
    # Code identification results
    target_files: List[Dict[str, Any]]
    modification_plan: Optional[Dict[str, Any]]
    identification_errors: List[str]
    
    # Code generation results
    generated_code: List[Dict[str, Any]]
    generation_errors: List[str]
    
    # Validation results
    validation_results: Optional[Dict[str, Any]]
    final_code: List[Dict[str, Any]]
    validation_errors: List[str]
    
    # Workflow metadata
    workflow_status: str  # 'running', 'completed', 'failed'
    current_step: str
    execution_log: List[str]
    start_time: str
    end_time: Optional[str]
    
    # Messages for inter-agent communication
    messages: Annotated[List[Dict], add_messages]


class CodeGenerationWorkflow:
    """Main workflow orchestrator using LangGraph"""
    
    def __init__(self):
        self.parser_agent = ParserAgent()
        self.code_identifier_agent = CodeIdentifierAgent()
        self.code_generator_agent = CodeGeneratorAgent()
        self.code_validator_agent = CodeValidatorAgent()
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create workflow graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes (agents)
        workflow.add_node("parse_config", self._parse_config_node)
        workflow.add_node("identify_code", self._identify_code_node)
        workflow.add_node("generate_code", self._generate_code_node)
        workflow.add_node("validate_code", self._validate_code_node)
        workflow.add_node("handle_validation_failure", self._handle_validation_failure_node)
        workflow.add_node("finalize_workflow", self._finalize_workflow_node)
        
        # Define the workflow edges
        workflow.set_entry_point("parse_config")
        
        # From parse_config
        workflow.add_conditional_edges(
            "parse_config",
            self._should_continue_after_parsing,
            {
                "continue": "identify_code",
                "end": END
            }
        )
        
        # From identify_code
        workflow.add_conditional_edges(
            "identify_code",
            self._should_continue_after_identification,
            {
                "continue": "generate_code",
                "end": END
            }
        )
        
        # From generate_code
        workflow.add_conditional_edges(
            "generate_code",
            self._should_continue_after_generation,
            {
                "continue": "validate_code",
                "end": END
            }
        )
        
        # From validate_code
        workflow.add_conditional_edges(
            "validate_code",
            self._should_continue_after_validation,
            {
                "success": "finalize_workflow",
                "retry": "handle_validation_failure",
                "end": END
            }
        )
        
        # From handle_validation_failure
        workflow.add_conditional_edges(
            "handle_validation_failure",
            self._should_retry_after_fix,
            {
                "retry": "generate_code",
                "end": END
            }
        )
        
        # From finalize_workflow
        workflow.add_edge("finalize_workflow", END)
        
        return workflow.compile()
    
    # Node implementations
    def _parse_config_node(self, state: WorkflowState) -> WorkflowState:
        """Parse configuration using ParserAgent"""
        logger.info("Starting configuration parsing...")
        
        state["current_step"] = "parsing_config"
        state["execution_log"].append(f"[{datetime.now()}] Starting config parsing")
        
        try:
            # Parse the configuration
            parsed_config = self.parser_agent.parse_config(state["config_data"])
            
            if parsed_config:
                # Validate the parsed configuration
                validation_result = self.parser_agent.validate_config(parsed_config)
                
                if validation_result["is_valid"]:
                    # Enrich with additional metadata
                    enriched_config = self.parser_agent.enrich_metadata(parsed_config)
                    
                    state["parsed_config"] = enriched_config
                    state["parsing_errors"] = []
                    state["execution_log"].append(f"[{datetime.now()}] Config parsing completed successfully")
                    
                    # Add success message
                    state["messages"].append({
                        "role": "parser",
                        "content": "Configuration parsed and validated successfully",
                        "metadata": {"parsed_sections": list(parsed_config.keys())}
                    })
                    
                else:
                    state["parsing_errors"] = validation_result["errors"]
                    state["execution_log"].append(f"[{datetime.now()}] Config validation failed")
                    logger.error(f"Config validation failed: {validation_result['errors']}")
            else:
                state["parsing_errors"] = ["Failed to parse configuration"]
                state["execution_log"].append(f"[{datetime.now()}] Config parsing failed")
                logger.error("Failed to parse configuration")
                
        except Exception as e:
            state["parsing_errors"] = [f"Parsing error: {str(e)}"]
            state["execution_log"].append(f"[{datetime.now()}] Config parsing error: {str(e)}")
            logger.error(f"Error in parsing: {e}")
        
        return state
    
    def _identify_code_node(self, state: WorkflowState) -> WorkflowState:
        """Identify target files and create modification plan"""
        logger.info("Starting code identification...")
        
        state["current_step"] = "identifying_code"
        state["execution_log"].append(f"[{datetime.now()}] Starting code identification")
        
        try:
            project_path = Path(state["project_path"])
            
            # Identify target files
            target_files = self.code_identifier_agent.identify_target_files(
                state["parsed_config"], project_path
            )
            
            if target_files:
                # Create modification plan
                modification_plan = self.code_identifier_agent.create_modification_plan(
                    target_files, state["parsed_config"]
                )
                
                state["target_files"] = target_files
                state["modification_plan"] = modification_plan
                state["identification_errors"] = []
                state["execution_log"].append(
                    f"[{datetime.now()}] Identified {len(target_files)} files for modification"
                )
                
                # Add success message
                state["messages"].append({
                    "role": "identifier",
                    "content": f"Identified {len(target_files)} files requiring modifications",
                    "metadata": {
                        "files": [f["file_path"] for f in target_files],
                        "complexity": modification_plan["estimated_complexity"]
                    }
                })
                
            else:
                state["identification_errors"] = ["No target files identified"]
                state["execution_log"].append(f"[{datetime.now()}] No target files found")
                logger.warning("No target files identified for modification")
                
        except Exception as e:
            state["identification_errors"] = [f"Identification error: {str(e)}"]
            state["execution_log"].append(f"[{datetime.now()}] Code identification error: {str(e)}")
            logger.error(f"Error in code identification: {e}")
        
        return state
    
    def _generate_code_node(self, state: WorkflowState) -> WorkflowState:
        """Generate code modifications"""
        logger.info("Starting code generation...")
        
        state["current_step"] = "generating_code"
        state["execution_log"].append(f"[{datetime.now()}] Starting code generation")
        
        try:
            # Generate code modifications
            generation_results = self.code_generator_agent.generate_code_modifications(
                state["modification_plan"]
            )
            
            if generation_results["modified_files"]:
                state["generated_code"] = generation_results["modified_files"]
                state["generation_errors"] = generation_results.get("errors", [])
                state["execution_log"].append(
                    f"[{datetime.now()}] Generated code for {len(generation_results['modified_files'])} files"
                )
                
                # Add success message
                state["messages"].append({
                    "role": "generator",
                    "content": f"Generated modifications for {len(generation_results['modified_files'])} files",
                    "metadata": {
                        "modified_files": len(generation_results['modified_files']),
                        "errors": len(generation_results.get('errors', []))
                    }
                })
                
            else:
                state["generation_errors"] = generation_results.get("errors", ["No code generated"])
                state["execution_log"].append(f"[{datetime.now()}] Code generation failed")
                logger.error("No code was generated")
                
        except Exception as e:
            state["generation_errors"] = [f"Generation error: {str(e)}"]
            state["execution_log"].append(f"[{datetime.now()}] Code generation error: {str(e)}")
            logger.error(f"Error in code generation: {e}")
        
        return state
    
    def _validate_code_node(self, state: WorkflowState) -> WorkflowState:
        """Validate generated code"""
        logger.info("Starting code validation...")
        
        state["current_step"] = "validating_code"
        state["execution_log"].append(f"[{datetime.now()}] Starting code validation")
        
        try:
            # Validate the generated code
            validation_results = self.code_validator_agent.validate_code_changes(
                state["generated_code"]
            )
            
            state["validation_results"] = validation_results
            state["validation_errors"] = validation_results.get("errors_found", [])
            
            if validation_results["overall_status"] == "passed":
                # Use fixed files if available, otherwise use generated code
                if validation_results.get("fixed_files"):
                    state["final_code"] = validation_results["fixed_files"]
                    state["execution_log"].append(
                        f"[{datetime.now()}] Code validated and auto-fixed"
                    )
                else:
                    state["final_code"] = state["generated_code"]
                    state["execution_log"].append(
                        f"[{datetime.now()}] Code validation passed"
                    )
                
                # Add success message
                state["messages"].append({
                    "role": "validator",
                    "content": "Code validation completed successfully",
                    "metadata": {
                        "status": validation_results["overall_status"],
                        "files_validated": len(validation_results["files_validated"]),
                        "auto_fixes": len(validation_results.get("fixed_files", []))
                    }
                })
                
            else:
                state["execution_log"].append(
                    f"[{datetime.now()}] Code validation failed with {len(validation_results['errors_found'])} errors"
                )
                logger.warning(f"Code validation failed: {validation_results['errors_found']}")
                
        except Exception as e:
            state["validation_errors"] = [f"Validation error: {str(e)}"]
            state["execution_log"].append(f"[{datetime.now()}] Code validation error: {str(e)}")
            logger.error(f"Error in code validation: {e}")
        
        return state
    
    def _handle_validation_failure_node(self, state: WorkflowState) -> WorkflowState:
        """Handle validation failures and attempt fixes"""
        logger.info("Handling validation failures...")
        
        state["current_step"] = "handling_validation_failure"
        state["execution_log"].append(f"[{datetime.now()}] Handling validation failures")
        
        try:
            # Check if we can auto-fix the issues
            if state["validation_results"] and state["validation_results"].get("fixed_files"):
                state["generated_code"] = [
                    {
                        "file_path": fixed["file_path"],
                        "modified_content": fixed["fixed_content"],
                        "original_content": fixed["original_content"]
                    }
                    for fixed in state["validation_results"]["fixed_files"]
                ]
                state["execution_log"].append(f"[{datetime.now()}] Applied auto-fixes")
            else:
                # Mark as failed if no fixes available
                state["workflow_status"] = "failed"
                state["execution_log"].append(f"[{datetime.now()}] No auto-fixes available")
                
        except Exception as e:
            state["validation_errors"].append(f"Fix handling error: {str(e)}")
            state["execution_log"].append(f"[{datetime.now()}] Error handling validation failure: {str(e)}")
            logger.error(f"Error handling validation failure: {e}")
        
        return state
    
    def _finalize_workflow_node(self, state: WorkflowState) -> WorkflowState:
        """Finalize the workflow and save results"""
        logger.info("Finalizing workflow...")
        
        state["current_step"] = "finalizing"
        state["end_time"] = datetime.now().isoformat()
        state["workflow_status"] = "completed"
        state["execution_log"].append(f"[{datetime.now()}] Workflow completed successfully")
        
        try:
            # Save the final results
            self._save_workflow_results(state)
            
            # Add final message
            state["messages"].append({
                "role": "workflow",
                "content": "Workflow completed successfully",
                "metadata": {
                    "files_modified": len(state.get("final_code", [])),
                    "execution_time": state["end_time"],
                    "status": "completed"
                }
            })
            
        except Exception as e:
            logger.error(f"Error finalizing workflow: {e}")
            state["execution_log"].append(f"[{datetime.now()}] Finalization error: {str(e)}")
        
        return state
    
    # Conditional edge functions
    def _should_continue_after_parsing(self, state: WorkflowState) -> str:
        """Determine if workflow should continue after parsing"""
        if state["parsing_errors"]:
            state["workflow_status"] = "failed"
            return "end"
        return "continue"
    
    def _should_continue_after_identification(self, state: WorkflowState) -> str:
        """Determine if workflow should continue after identification"""
        if state["identification_errors"] or not state.get("target_files"):
            state["workflow_status"] = "failed"
            return "end"
        return "continue"
    
    def _should_continue_after_generation(self, state: WorkflowState) -> str:
        """Determine if workflow should continue after generation"""
        if state["generation_errors"] or not state.get("generated_code"):
            state["workflow_status"] = "failed"
            return "end"
        return "continue"
    
    def _should_continue_after_validation(self, state: WorkflowState) -> str:
        """Determine next step after validation"""
        if not state.get("validation_results"):
            state["workflow_status"] = "failed"
            return "end"
            
        if state["validation_results"]["overall_status"] == "passed":
            return "success"
        elif state["validation_results"].get("fixed_files"):
            return "retry"
        else:
            return "retry"
    
    def _should_retry_after_fix(self, state: WorkflowState) -> str:
        """Determine if workflow should retry after attempting fixes"""
        # Implement retry logic (e.g., max retries)
        retry_count = getattr(state, '_retry_count', 0)
        if retry_count < 2:  # Max 2 retries
            state['_retry_count'] = retry_count + 1
            return "retry"
        else:
            state["workflow_status"] = "failed"
            return "end"
    
    def _save_workflow_results(self, state: WorkflowState):
        """Save workflow results to output directory"""
        try:
            output_dir = Path("output/generated_code")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save final code files
            if state.get("final_code"):
                for file_info in state["final_code"]:
                    file_path = Path(file_info["file_path"])
                    output_file = output_dir / file_path.name
                    
                    # Use fixed_content if available, otherwise modified_content
                    content = file_info.get("fixed_content", file_info.get("modified_content"))
                    FileHandler.write_file(output_file, content)
            
            # Save workflow metadata
            metadata = {
                "start_time": state["start_time"],
                "end_time": state["end_time"],
                "status": state["workflow_status"],
                "execution_log": state["execution_log"],
                "files_processed": len(state.get("final_code", [])),
                "messages": state.get("messages", [])
            }
            
            metadata_file = output_dir / "workflow_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"Workflow results saved to {output_dir}")
            
        except Exception as e:
            logger.error(f"Error saving workflow results: {e}")
    
    def run_workflow(self, config_data: Dict[str, Any], project_path: str) -> Dict[str, Any]:
        """Run the complete workflow"""
        
        # Initialize state
        initial_state = WorkflowState(
            config_data=config_data,
            project_path=project_path,
            parsed_config=None,
            parsing_errors=[],
            target_files=[],
            modification_plan=None,
            identification_errors=[],
            generated_code=[],
            generation_errors=[],
            validation_results=None,
            final_code=[],
            validation_errors=[],
            workflow_status="running",
            current_step="initializing",
            execution_log=[],
            start_time=datetime.now().isoformat(),
            end_time=None,
            messages=[]
        )
        
        logger.info("Starting AI Code Generation Workflow")
        initial_state["execution_log"].append(f"[{datetime.now()}] Workflow started")
        
        try:
            # Run the workflow
            final_state = self.workflow.invoke(initial_state)
            
            logger.info(f"Workflow completed with status: {final_state['workflow_status']}")
            
            return {
                "status": final_state["workflow_status"],
                "files_modified": len(final_state.get("final_code", [])),
                "execution_log": final_state["execution_log"],
                "errors": (
                    final_state.get("parsing_errors", []) +
                    final_state.get("identification_errors", []) +
                    final_state.get("generation_errors", []) +
                    final_state.get("validation_errors", [])
                ),
                "final_state": final_state
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "status": "failed",
                "files_modified": 0,
                "execution_log": initial_state["execution_log"] + [f"[{datetime.now()}] Workflow failed: {str(e)}"],
                "errors": [f"Workflow execution error: {str(e)}"],
                "final_state": initial_state
            }


# Factory function for easy workflow creation
def create_workflow() -> CodeGenerationWorkflow:
    """Create and return a new workflow instance"""
    return CodeGenerationWorkflow()


# Example usage function
def run_code_generation_workflow(config_file_path: str, project_path: str) -> Dict[str, Any]:
    """
    Convenience function to run the workflow with a config file
    
    Args:
        config_file_path: Path to the configuration JSON file
        project_path: Path to the project directory to modify
        
    Returns:
        Dict containing workflow results
    """
    try:
        # Load configuration
        config_data = FileHandler.read_json_file(Path(config_file_path))
        if not config_data:
            return {
                "status": "failed",
                "errors": ["Failed to load configuration file"],
                "files_modified": 0
            }
        
        # Create and run workflow
        workflow = create_workflow()
        return workflow.run_workflow(config_data, project_path)
        
    except Exception as e:
        return {
            "status": "failed",
            "errors": [f"Error running workflow: {str(e)}"],
            "files_modified": 0
        }