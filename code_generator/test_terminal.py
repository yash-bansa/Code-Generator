#!/usr/bin/env python3
"""
Terminal-based AI Code Generator
Run with: python test_terminal.py
"""

import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import TypedDict, List, Dict, Any
import copy

# Import your agents
from agents.QueryRephraseAgent import QueryRephraseAgent
from agents.parser_agent import ParserAgent
from agents.master_planner_agent import MasterPlannerAgent
from agents.delta_analyzer_agent import DeltaAnalyzerAgent
from agents.code_generator_agent import CodeGeneratorAgent  
from agents.code_validator_agent import CodeValidatorAgent
from config.settings import settings

# Setup logging for terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('code_generator.log')
    ]
)
logger = logging.getLogger(__name__)

# ----------- State Definition --------------
class BotState(TypedDict):
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

# ---------- Initialize Agents ------------------------
print("🤖 Initializing AI Code Generator...")
print("=" * 60)

try:
    rephrase_agent = QueryRephraseAgent()
    parser_agent = ParserAgent()
    master_planner_agent = MasterPlannerAgent()
    delta_analyzer_agent = DeltaAnalyzerAgent()
    code_generator_agent = CodeGeneratorAgent()  
    validator_agent = CodeValidatorAgent()
    print("✅ All agents initialized successfully!")
except Exception as e:
    print(f"❌ Failed to initialize agents: {e}")
    sys.exit(1)

# ---------- Processing Functions ---------------
async def rephrase_query(state: BotState) -> BotState:
    """Process and rephrase user query"""
    print("\n🔄 STEP 1: Processing Query...")
    print("-" * 40)
    
    try:
        print(f"📝 User Query: {state['latest_query']}")
        
        response = await rephrase_agent.rephrase_query(
            state["latest_query"],
            state["user_history"]
        )
        print(state["user_history"])
        
        if response:
            state["developer_task"] = response.get("developer_task", "")
            state["is_satisfied"] = response.get("is_satisfied", False)
            state["suggestions"] = response.get("suggestions", [])
            
            print(f"🎯 Developer Task: {state['developer_task']}")
            print(f"✅ Query Satisfied: {state['is_satisfied']}")
            
            if not state["is_satisfied"]:
                print("\n💡 Suggestions for improvement:")
                for i, suggestion in enumerate(state["suggestions"], 1):
                    print(f"   {i}. {suggestion}")
        else:
            print("⚠️ Empty response from rephrase agent")
            state["is_satisfied"] = False
            state["suggestions"] = ["Please provide more specific details about your task."]
            
    except Exception as e:
        print(f"❌ Error in query processing: {e}")
        state["is_satisfied"] = False
        state["suggestions"] = [f"Error processing query: {str(e)}"]
    
    return state

async def parse_configuration(state: BotState) -> BotState:
    """Parse configuration files"""
    print("\n🔄 STEP 2: Parsing Configuration...")
    print("-" * 40)
    
    try:
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
                    print(f"✅ Loaded config from: {config_path}")
                    break
            except Exception as e:
                print(f"⚠️ Failed to load {config_path}: {e}")
                continue
        
        if not config_data:
            print("⚠️ No config file found, using default minimal configuration")
            config_data = {
                "data_sources": [],
                "transformations": [],
                "outputs": [],
                "processing_config": {"batch_size": 1000}
            }
        
        print("🔄 Parsing configuration with AI...")
        parsed = await parser_agent.parse_config(config_data)
        
        if parsed:
            validated = parser_agent.validate_config(parsed)
            parsed["validation"] = validated
            print("✅ Configuration parsed and validated")
            
            # Show validation results
            if validated.get("is_valid"):
                print("✅ Configuration validation passed")
            else:
                print("⚠️ Configuration validation warnings:")
                for error in validated.get("errors", []):
                    print(f"   - {error}")
        else:
            parsed = config_data
            print("⚠️ AI parser failed, using original config")
        
        state["parsed_config"] = parsed
        
    except Exception as e:
        print(f"❌ Error in configuration parsing: {e}")
        state["parsed_config"] = {
            "data_sources": [],
            "transformations": [],
            "outputs": [],
            "error": f"Configuration parsing failed: {str(e)}"
        }
    
    return state

async def identify_files(state: BotState) -> BotState:
    """Identify target files for modification"""
    print("\n🔄 STEP 3: Identifying Target Files...")
    print("-" * 40)
    
    try:
        print(f"📁 Scanning project path: {settings.PROJECT_ROOT_PATH}")
        
        result = await master_planner_agent.identify_target_files(
            parsed_config=state["parsed_config"],
            project_path=settings.PROJECT_ROOT_PATH,
            user_question=state["developer_task"]
        )
        
        print(f"✅ Identified {len(result)} target files")
        
        # Show identified files
        if result:
            print("\n📋 Files to be modified:")
            for i, file_info in enumerate(result, 1):
                file_path = file_info.get("file_path", "Unknown")
                priority = file_info.get("priority", "medium")
                print(f"   {i}. {Path(file_path).name} (Priority: {priority})")
        
        print("\n🔄 Creating modification plan...")
        mod_plan = await delta_analyzer_agent.create_modification_plan(
            result, 
            state["parsed_config"]
        )
        
        state["identified_files"] = result
        state["modification_plan"] = mod_plan
        
        # Show plan summary
        files_to_modify = mod_plan.get("files_to_modify", [])
        print(f"✅ Modification plan created for {len(files_to_modify)} files")
        
        if mod_plan.get("estimated_complexity"):
            print(f"📊 Estimated complexity: {mod_plan['estimated_complexity']}")
        
    except Exception as e:
        print(f"❌ Error in file identification: {e}")
        state["identified_files"] = []
        state["modification_plan"] = {"files_to_modify": [], "errors": [str(e)]}
    
    return state

async def generate_code(state: BotState) -> BotState:
    """Generate code modifications"""
    print("\n🔄 STEP 4: Generating Code...")
    print("-" * 40)
    
    try:
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
            print("⚠️ No files to modify")
            full_result["warnings"].append("No files identified for modification")
            state["generated_code"] = full_result
            return state
        
        full_result["processing_summary"]["total_files"] = len(files)
        
        print(f"🔄 Processing {len(files)} files...")
        
        for i, file_mod in enumerate(files, 1):
            try:
                file_path = file_mod.get("file_path", "unknown")
                file_name = Path(file_path).name
                
                print(f"\n📄 Processing file {i}/{len(files)}: {file_name}")
                print(f"   Path: {file_path}")
                
                # Create single file modification plan
                single_plan = copy.deepcopy(state["modification_plan"])
                single_plan["files_to_modify"] = [file_mod]
                single_plan["execution_order"] = [file_path]
                
                # Generate code with timeout
                print("   🤖 Generating modifications...")
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
                        print(f"   ✅ Successfully processed {file_name}")
                    else:
                        error_msg = f"Empty result for {file_path}"
                        full_result["errors"].append(error_msg)
                        full_result["processing_summary"]["failed"] += 1
                        print(f"   ❌ {error_msg}")
                        
                except asyncio.TimeoutError:
                    error_msg = f"Timeout processing {file_path}"
                    full_result["errors"].append(error_msg)
                    full_result["processing_summary"]["failed"] += 1
                    print(f"   ⏰ {error_msg}")
                    
            except Exception as e:
                error_msg = f"{file_mod.get('file_path', 'unknown')}: {str(e)}"
                full_result["errors"].append(error_msg)
                full_result["processing_summary"]["failed"] += 1
                print(f"   ❌ File processing error: {error_msg}")
            
            # Brief pause between files
            await asyncio.sleep(1)
        
        # Show summary
        print(f"\n📊 Code Generation Summary:")
        print(f"   ✅ Successful: {full_result['processing_summary']['successful']}")
        print(f"   ❌ Failed: {full_result['processing_summary']['failed']}")
        print(f"   📄 Modified files: {len(full_result['modified_files'])}")
        
        if full_result["errors"]:
            print(f"\n⚠️ Errors encountered:")
            for error in full_result["errors"]:
                print(f"   - {error}")
        
        state["generated_code"] = full_result
        
    except Exception as e:
        print(f"❌ Error in code generation: {e}")
        state["generated_code"] = {
            "modified_files": [],
            "errors": [f"Code generation failed: {str(e)}"]
        }
    
    return state

async def validate_code(state: BotState) -> BotState:
    """Validate generated code"""
    print("\n🔄 STEP 5: Validating Generated Code...")
    print("-" * 40)
    
    try:
        modified_files = state["generated_code"].get("modified_files", [])
        
        if not modified_files:
            print("⚠️ No modified files to validate")
            state["validation_result"] = {
                "overall_status": "skipped",
                "message": "No files to validate"
            }
            return state
        
        print(f"🔍 Validating {len(modified_files)} modified files...")
        
        # Initial validation
        validated = await validator_agent.validate_code_changes(modified_files)
        state["validation_result"] = validated
        
        # Show validation results
        status = validated.get("overall_status", "unknown")
        print(f"📊 Validation Status: {status}")
        
        if status == "passed":
            print("✅ All validations passed!")
            
            # Save successful results
            try:
                await save_successful_results(
                    validated,
                    modified_files,
                    output_dir="output_new_1/generated_code"
                )
                print("💾 Results saved successfully!")
                
            except Exception as e:
                print(f"⚠️ Validation passed but failed to save: {e}")
        
        else:
            print("⚠️ Validation failed, attempting smart retry...")
            
            # Smart retry with different strategies
            max_retries = 2
            retry_strategies = ["conservative", "focused"]
            
            for retry_num in range(max_retries):
                try:
                    print(f"\n🔄 Retry attempt {retry_num + 1}/{max_retries} ({retry_strategies[retry_num]} strategy)...")
                    
                    retry_result = await intelligent_retry(
                        state,
                        strategy=retry_strategies[retry_num],
                        validation_errors=validated.get("errors_found", [])
                    )
                    
                    if retry_result and retry_result.get("overall_status") == "passed":
                        print(f"✅ Retry {retry_num + 1} succeeded!")
                        
                        # Update state with successful retry
                        state.update(retry_result["state_updates"])
                        state["validation_result"] = retry_result["validation"]
                        
                        await save_successful_results(
                            retry_result["validation"],
                            retry_result["modified_files"],
                            output_dir="output_new_1/generated_code"
                        )
                        
                        print("💾 Retry results saved successfully!")
                        break
                        
                except Exception as e:
                    print(f"❌ Retry {retry_num + 1} failed: {e}")
                    continue
            
            else:
                print("❌ All retry attempts failed")
        
        # Show detailed validation results
        errors = validated.get("errors_found", [])
        warnings = validated.get("warnings", [])
        
        if errors:
            print(f"\n❌ Validation Errors ({len(errors)}):")
            for error in errors:
                print(f"   - {error}")
        
        if warnings:
            print(f"\n⚠️ Validation Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"   - {warning}")
    
    except Exception as e:
        print(f"❌ Error in validation: {e}")
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
        print(f"❌ Intelligent retry failed: {e}")
    
    return None

async def save_successful_results(validation_result: Dict[str, Any], modified_files: List[Dict[str, Any]], output_dir: str):
    """Save successful results"""
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print(f"💾 Saving results to: {output_path}")
        
        # Save validation report
        with open(output_path / "validation_report.json", "w") as f:
            json.dump(validation_result, f, indent=2)
        print("   ✅ Validation report saved")
        
        # Save modified files
        for file_data in modified_files:
            file_path = file_data.get("file_path", "")
            if file_path:
                relative_path = Path(file_path).name
                output_file = output_path / f"modified_{relative_path}"
                
                with open(output_file, "w") as f:
                    f.write(file_data.get("modified_content", ""))
                print(f"   ✅ Saved: {output_file}")
        
        print(f"✅ All results saved to {output_dir}")
        
    except Exception as e:
        print(f"❌ Failed to save results: {e}")
        raise

# ---------- Main Processing Pipeline ---------------
async def process_query(user_query: str, history: List[str] = None) -> BotState:
    """Main processing pipeline"""
    
    # Initialize state
    state: BotState = {
        "user_history": history or [],
        "latest_query": user_query,
        "developer_task": "",
        "is_satisfied": False,
        "suggestions": [],
        "parsed_config": {},
        "identified_files": [],
        "modification_plan": {},
        "generated_code": {},
        "validation_result": {}
    }
    
    # Step 1: Rephrase Query
    state = await rephrase_query(state)
    
    if not state["is_satisfied"]:
        return state
    
    # Step 2: Parse Configuration
    state = await parse_configuration(state)
    
    # Step 3: Identify Files
    state = await identify_files(state)
    
    # Step 4: Generate Code
    state = await generate_code(state)
    
    # Step 5: Validate Code
    state = await validate_code(state)
    
    return state

def display_results(state: BotState):
    """Display final results"""
    print("\n" + "=" * 60)
    print("🎉 PROCESSING COMPLETE")
    print("=" * 60)
    
    # Show final status
    if state["is_satisfied"]:
        print("✅ Task Status: COMPLETED")
        print(f"🎯 Developer Task: {state['developer_task']}")
        
        # Show generated files
        modified_files = state["generated_code"].get("modified_files", [])
        if modified_files:
            print(f"\n📄 Generated Files ({len(modified_files)}):")
            for i, file in enumerate(modified_files, 1):
                file_path = file.get("file_path", "unknown")
                mods_applied = file.get("modifications_applied", 0)
                print(f"   {i}. {Path(file_path).name} ({mods_applied} modifications)")
        
        # Show validation status
        validation_status = state["validation_result"].get("overall_status", "unknown")
        if validation_status == "passed":
            print("\n✅ Validation: PASSED")
        elif validation_status == "skipped":
            print("\n⏭️ Validation: SKIPPED")
        else:
            print(f"\n⚠️ Validation: {validation_status.upper()}")
        
    else:
        print("❌ Task Status: INCOMPLETE")
        print("\n💡 Suggestions:")
        for suggestion in state["suggestions"]:
            print(f"   - {suggestion}")

# ---------- Interactive Terminal Interface ---------------
def get_user_input() -> str:
    """Get user input from terminal"""
    print("\n" + "=" * 60)
    print("🤖 AI CODE GENERATOR")
    print("=" * 60)
    print("Describe your development task below:")
    print("(Type 'exit' to quit, 'examples' to see examples)")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n💬 Your task: ").strip()
            
            if user_input.lower() == 'exit':
                print("👋 Goodbye!")
                sys.exit(0)
            elif user_input.lower() == 'examples':
                show_examples()
                continue
            elif user_input:
                return user_input
            else:
                print("⚠️ Please enter a task description.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            sys.exit(0)
        except EOFError:
            print("\n\n👋 Goodbye!")
            sys.exit(0)

def show_examples():
    """Show example prompts"""
    examples = [
        "Create an ETL pipeline to extract data from MySQL and generate Excel reports",
        "Build a REST API to manage user authentication and data access", 
        "Develop a data analysis script to process CSV files and create visualizations",
        "Create a web scraper to collect product information from e-commerce sites",
        "Build a data processing pipeline for real-time analytics",
        "Create automated testing scripts for existing codebase"
    ]
    
    print("\n💡 Example Tasks:")
    print("-" * 40)
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example}")

# ---------- Main Entry Point ---------------
async def main():
    """Main entry point"""
    try:
        # Show configuration
        print(f"⚙️ Configuration:")
        print(f"   Provider: {settings.LM_CLIENT_PROVIDER}")
        print(f"   Project Path: {settings.PROJECT_ROOT_PATH}")
        print(f"   Output Path: {settings.OUTPUT_PATH}")
        
        # Interactive mode
        history = []
        
        while True:
            # Get user input
            user_query = get_user_input()
            history.append(user_query)
            
            # Process the query
            print(f"\n🚀 Starting processing pipeline...")
            start_time = asyncio.get_event_loop().time()
            
            result = await process_query(user_query, history)
            
            end_time = asyncio.get_event_loop().time()
            processing_time = end_time - start_time
            
            # Display results
            display_results(result)
            
            print(f"\n⏱️ Total processing time: {processing_time:.2f} seconds")
            
            # Ask if user wants to continue
            print("\n" + "-" * 60)
            continue_choice = input("Do you want to process another task? (y/n): ").strip().lower()
            
            if continue_choice not in ['y', 'yes']:
                print("👋 Thank you for using AI Code Generator!")
                break
    
    except Exception as e:
        print(f"\n❌ Critical error: {e}")
        logger.exception("Critical error in main")
        sys.exit(1)

if __name__ == "__main__":
    # Run the terminal application
    asyncio.run(main())