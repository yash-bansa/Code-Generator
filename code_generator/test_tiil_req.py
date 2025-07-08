import asyncio
import sys
import json
import logging
from pathlib import Path
from langgraph.graph import StateGraph
from typing import List, Union
from pydantic import BaseModel
from agents import CommunicationAgent, QueryRephraserAgent, MasterPlannerAgent
from config.agents_io import (
    BotStateSchema,
    CommunicationInput,
    CommunicationOutput,
    QueryEnhancerInput,
    QueryEnhancerOutput,
    MasterPlannerInput,
    MasterPlannerOutput
)
from config.settings import settings

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

# ---------- Redis Connection ----------
redis_client = settings.get_redis_connection()

# ---------- Agent Initialization ----------
print("\nInitializing LangGraph-style Query Agents...")
communication_agent = CommunicationAgent()
query_rephraser_agent = QueryRephraserAgent()
master_planner_agent = MasterPlannerAgent()
print("Agents initialized successfully!")

# ---------- Helper Functions ----------
def get_user_history(user_id: str = "default_user") -> List[str]:
    """Get user history from Redis."""
    history_key = f"user:{user_id}:history"
    try:
        if redis_client:
            history = redis_client.lrange(history_key, 0, -1)
            return history if history else []
        else:
            logger.warning("Redis not available, using empty history")
            return []
    except Exception as e:
        logger.error(f"Error getting history from Redis: {e}")
        return []

def save_to_history(user_id: str, query: str):
    """Save query to user history in Redis."""
    history_key = f"user:{user_id}:history"
    try:
        if redis_client:
            redis_client.rpush(history_key, query)
            # Keep only last 50 queries to prevent unlimited growth
            redis_client.ltrim(history_key, -50, -1)
            logger.debug(f"Saved query to Redis for user {user_id}")
        else:
            logger.warning("Redis not available, query not saved")
    except Exception as e:
        logger.error(f"Error saving to Redis: {e}")

def clear_user_history(user_id: str = "default_user") -> bool:
    """Clear user history from Redis."""
    history_key = f"user:{user_id}:history"
    try:
        if redis_client:
            if redis_client.exists(history_key):
                redis_client.delete(history_key)
                logger.info(f"Cleared history for user {user_id}")
                return True
            else:
                logger.info(f"No history found for user {user_id}")
                return False
        else:
            logger.warning("Redis not available, cannot clear history")
            return False
    except Exception as e:
        logger.error(f"Error clearing history from Redis: {e}")
        return False

def delete_user_completely(user_id: str = "default_user") -> bool:
    """Completely delete user and all associated data from Redis."""
    try:
        if redis_client:
            # Find all keys related to this user
            user_pattern = f"user:{user_id}:*"
            user_keys = redis_client.keys(user_pattern)
            
            if user_keys:
                # Delete all user-related keys
                deleted_count = redis_client.delete(*user_keys)
                logger.info(f"Deleted {deleted_count} keys for user {user_id}")
                return True
            else:
                logger.info(f"No data found for user {user_id}")
                return False
        else:
            logger.warning("Redis not available, cannot delete user")
            return False
    except Exception as e:
        logger.error(f"Error deleting user from Redis: {e}")
        return False

def get_all_users() -> List[str]:
    """Get list of all users in Redis."""
    try:
        if redis_client:
            # Find all user keys
            user_keys = redis_client.keys("user:*:history")
            # Extract user IDs from keys
            users = []
            for key in user_keys:
                # Extract user_id from "user:user_id:history"
                parts = key.split(":")
                if len(parts) >= 3:
                    user_id = parts[1]
                    users.append(user_id)
            return users
        else:
            logger.warning("Redis not available")
            return []
    except Exception as e:
        logger.error(f"Error getting users from Redis: {e}")
        return []

def get_redis_cache_info():
    """Get Redis cache information."""
    try:
        if redis_client:
            info = redis_client.info()
            all_keys = redis_client.keys("*")
            user_keys = redis_client.keys("user:*")
            
            cache_info = {
                "total_keys": len(all_keys),
                "user_keys": len(user_keys),
                "memory_used": info.get('used_memory_human', 'Unknown'),
                "connected_clients": info.get('connected_clients', 'Unknown'),
                "total_commands": info.get('total_commands_processed', 'Unknown')
            }
            return cache_info
        else:
            return {"error": "Redis not available"}
    except Exception as e:
        logger.error(f"Error getting Redis info: {e}")
        return {"error": str(e)}

def show_history_info(user_id: str = "default_user"):
    """Show user history information."""
    history = get_user_history(user_id)
    if history:
        print(f"\n📚 Conversation History for '{user_id}' ({len(history)} queries):")
        print("-" * 50)
        for i, query in enumerate(history, 1):
            # Truncate long queries for display
            display_query = query[:60] + "..." if len(query) > 60 else query
            print(f"   {i:2d}. {display_query}")
        print("-" * 50)
    else:
        print(f"\n No conversation history found for user '{user_id}'")

def show_cache_stats():
    """Show Redis cache statistics."""
    print("\n Redis Cache Statistics:")
    print("-" * 40)
    
    cache_info = get_redis_cache_info()
    if "error" not in cache_info:
        print(f" Total Keys: {cache_info['total_keys']}")
        print(f" User Keys: {cache_info['user_keys']}")
        print(f" Memory Used: {cache_info['memory_used']}")
        print(f" Connected Clients: {cache_info['connected_clients']}")
        print(f" Total Commands: {cache_info['total_commands']}")
        
        # Show all users
        users = get_all_users()
        if users:
            print(f"\n Active Users ({len(users)}):")
            for user in users:
                history_count = len(get_user_history(user))
                print(f"   • {user} ({history_count} queries)")
        else:
            print("\n No active users found")
    else:
        print(f" Error: {cache_info['error']}")
    
    print("-" * 40)

# ---------- Helper to ensure correct schema ----------
def ensure_state_schema(state: Union[dict, BaseModel]) -> BotStateSchema:
    if isinstance(state, BotStateSchema):
        return state
    return BotStateSchema(**state)

# ---------- Helper to print detailed plan ----------
def print_detailed_plan(files_to_modify: List):
    """Print detailed plan for each file."""
    if not files_to_modify:
        print("📝 No detailed plan available.")
        return
    
    print("\n📋 DETAILED MODIFICATION PLAN")
    print("=" * 70)
    
    for i, file_info in enumerate(files_to_modify, 1):
        print(f"\n File {i}: {file_info.file_path}")
        print(f" Priority: {file_info.priority}")
        
        # Print analysis details
        if hasattr(file_info, 'analysis') and file_info.analysis:
            analysis = file_info.analysis
            print(f"   Analysis:")
            print(f"   • Needs Modification: {analysis.needs_modification}")
            print(f"   • Modification Type: {analysis.modification_type}")
            print(f"   • Reason: {analysis.reason}")
            
            # Print suggested changes
            if hasattr(analysis, 'suggested_changes') and analysis.suggested_changes:
                print(f"   • Suggested Changes:")
                for j, change in enumerate(analysis.suggested_changes, 1):
                    print(f"     {j}. Type: {change.type}")
                    print(f"        Target: {change.target}")
                    print(f"        Description: {change.description}")
            
            # Print cross-file dependencies
            if hasattr(analysis, 'cross_file_dependencies') and analysis.cross_file_dependencies:
                print(f"   • Cross-file Dependencies:")
                for dep in analysis.cross_file_dependencies:
                    print(f"     - {dep.source_file} → {dep.target_file}")
                    print(f"       Element: {dep.linked_element} ({dep.type})")
                    print(f"       Reason: {dep.reason}")
        
        # Print file structure if available
        if hasattr(file_info, 'structure') and file_info.structure:
            structure = file_info.structure
            print(f" File Structure:")
            
            if structure.get('functions'):
                print(f"   • Functions: {[f.get('name', 'Unknown') for f in structure['functions']]}")
            
            if structure.get('classes'):
                print(f"   • Classes: {[c.get('name', 'Unknown') for c in structure['classes']]}")
            
            if structure.get('imports'):
                print(f"   • Imports: {structure['imports']}")
        
        # Print file info if available
        if hasattr(file_info, 'file_info') and file_info.file_info:
            file_info_details = file_info.file_info
            print(f"ℹ File Info:")
            if file_info_details.get('size'):
                print(f"   • Size: {file_info_details['size']} bytes")
            if file_info_details.get('last_modified'):
                print(f"   • Last Modified: {file_info_details['last_modified']}")
            if file_info_details.get('lines'):
                print(f"   • Lines of Code: {file_info_details['lines']}")
        
        print("-" * 70)

def show_help():
    """Show available commands."""
    print("\n  Available Commands:")
    print("  • Type your query to process it")
    print("  • 'history' - Show your conversation history")
    print("  • 'clear' or 'clear history' - Clear your conversation history")
    print("  • 'delete user' - Completely delete current user from Redis")
    print("  • 'delete user <user_id>' - Delete specific user from Redis")
    print("  • 'users' - Show all users in Redis")
    print("  • 'cache' - Show Redis cache statistics")
    print("  • 'user <user_id>' - Switch to different user")
    print("  • 'help' - Show this help message")
    print("  • 'exit' or 'quit' - Exit the application")

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

async def master_planner_node(state: dict) -> dict:
    state_obj = ensure_state_schema(state)
    logger.info("Master Planner Node: Identifying target files...")
    
    try:
        # Load configuration from the specified path
        config_path = Path("./examples/sample_config.json")
        
        if not config_path.exists():
            logger.warning(f"Config file not found at {config_path}. Creating default config...")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            default_config = {
                "project_type": "python",
                "framework": "general",
                "main_files": ["main.py", "app.py"],
                "config_files": ["config.py", "settings.py"]
            }
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default config at: {config_path}")
        
        # Load the configuration
        with open(config_path, 'r') as f:
            parsed_config = json.load(f)
        
        # Prepare project path (same directory as config for this example)
        project_path = config_path.parent / "sample_project"
        if not project_path.exists():
            project_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created project directory at: {project_path}")
        
        # Create Master Planner input
        planner_input = MasterPlannerInput(
            parsed_config=parsed_config,
            project_path=project_path,
            user_question=state_obj.developer_task
        )
        
        # Call Master Planner agent
        result: MasterPlannerOutput = await master_planner_agent.identify_target_files(planner_input)
        
        # Update state with results
        state_obj.master_planner_result = result.files_to_modify
        state_obj.master_planner_success = result.success
        state_obj.master_planner_message = result.message
        
        logger.info(f"Master Planner Success: {result.success}")
        logger.info(f"Master Planner Message: {result.message}")
        logger.info(f"Files to Modify: {len(result.files_to_modify)}")
        logger.info(f"The final result is: {result}")
        
    except Exception as e:
        logger.error(f"Error in Master Planner Node: {e}")
        state_obj.master_planner_success = False
        state_obj.master_planner_message = f"Error: {str(e)}"
        state_obj.master_planner_result = []
    
    return state_obj.dict()

# ---------- Conditional Logic ----------
def should_proceed_to_master_planner(state: dict) -> str:
    """Determine whether to proceed to master planner or end"""
    state_obj = ensure_state_schema(state)
    if state_obj.is_satisfied:
        return "master_planner"
    else:
        return "__end__"

def should_retry_after_master_planner(state: dict) -> str:
    """Determine whether to retry or end after master planner"""
    state_obj = ensure_state_schema(state)
    if state_obj.master_planner_success:
        # Master planner succeeded, we're done
        return "__end__"
    else:
        # ✅ Master planner failed, but don't auto-retry - let main loop handle it
        return "__end__"

# ---------- Run LangGraph Flow ----------
async def main():
    print("\nWelcome to the LangGraph Query Clarifier")
    print("=" * 60)
    
    # Get user ID (you could make this interactive or configurable)
    current_user = "default_user"
    print(f" Current user: {current_user}")
    
    # Load existing history from Redis
    history = get_user_history(current_user)
    if history:
        print(f" Loaded {len(history)} previous queries from session")
    
    show_help()
    
    while True:
        user_input = input(f"\n[{current_user}] Enter your query: ").strip()
        if not user_input:
            print("Please enter a valid input.")
            continue
            
        # Handle special commands
        if user_input.lower() in ["exit", "quit", "q"]:
            print(" Goodbye!")
            break
        elif user_input.lower() == "help":
            show_help()
            continue
        elif user_input.lower() in ["clear", "clear history"]:
            if clear_user_history(current_user):
                print(f" History cleared for user '{current_user}'")
                history = []  # Reset local history too
            else:
                print(f" No history found for user '{current_user}' or Redis unavailable")
            continue
        elif user_input.lower() == "delete user":
            # Delete current user
            confirm = input(f" Are you sure you want to completely delete user '{current_user}' from Redis? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                if delete_user_completely(current_user):
                    print(f" User '{current_user}' completely deleted from Redis")
                    history = []  # Reset local history
                else:
                    print(f" No data found for user '{current_user}' or Redis unavailable")
            else:
                print(" Operation cancelled")
            continue
        elif user_input.lower().startswith("delete user "):
            # Delete specific user
            target_user = user_input[12:].strip()
            if target_user:
                confirm = input(f" Are you sure you want to completely delete user '{target_user}' from Redis? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    if delete_user_completely(target_user):
                        print(f" User '{target_user}' completely deleted from Redis")
                        # If we deleted current user, reset local history
                        if target_user == current_user:
                            history = []
                    else:
                        print(f" No data found for user '{target_user}' or Redis unavailable")
                else:
                    print(" Operation cancelled")
            else:
                print("Please provide a valid user ID")
            continue
        elif user_input.lower() == "users":
            users = get_all_users()
            if users:
                print(f"\n👥 Active Users ({len(users)}):")
                for user in users:
                    history_count = len(get_user_history(user))
                    status = " (current)" if user == current_user else ""
                    print(f"   • {user} ({history_count} queries){status}")
            else:
                print("\n👥 No active users found in Redis")
            continue
        elif user_input.lower() == "cache":
            show_cache_stats()
            continue
        elif user_input.lower() == "history":
            show_history_info(current_user)
            continue
        elif user_input.lower().startswith("user "):
            new_user = user_input[5:].strip()
            if new_user:
                current_user = new_user
                # Load history for new user
                history = get_user_history(current_user)
                print(f"👤 Switched to user: {current_user}")
                if history:
                    print(f" Loaded {len(history)} queries for this user")
            else:
                print("Please provide a valid user ID")
            continue
        
        # Process regular query
        user_query = user_input
        
        # Save query to Redis and update local history
        save_to_history(current_user, user_query)
        history.append(user_query)
        
        # ✅ Keep retrying until Master Planner succeeds or user gives up
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            state = BotStateSchema(
                latest_query=user_query,
                user_history=history
            )
            
            # Build LangGraph with simplified flow (no auto-retry loop)
            builder = StateGraph(dict)
            builder.add_node("communication_node", communication_node)
            builder.add_node("query_enhancement_node", query_enhancement_node)
            builder.add_node("master_planner_node", master_planner_node)
            
            builder.set_entry_point("communication_node")
            builder.add_edge("communication_node", "query_enhancement_node")
            
            # Add conditional edge: only go to master planner if satisfied
            builder.add_conditional_edges(
                "query_enhancement_node",
                should_proceed_to_master_planner,
                {
                    "master_planner": "master_planner_node",
                    "__end__": "__end__"
                }
            )
            
            # ✅ FIXED: No auto-retry loop in graph - just end
            builder.add_conditional_edges(
                "master_planner_node",
                should_retry_after_master_planner,
                {
                    "__end__": "__end__"
                }
            )
            
            graph = builder.compile()
            
            if retry_count == 0:
                print("\nLangGraph Structure:")
                try:
                    ascii_art = graph.get_graph().draw_ascii()
                    print(ascii_art)
                except Exception as e:
                    logger.warning(f"Unable to draw graph structure: {e}")
            
            # Run the graph
            try:
                final_state_dict = await graph.ainvoke(state.dict())
                final_state = BotStateSchema(**final_state_dict)
            except Exception as e:
                logger.error(f"Graph execution error: {e}")
                print(f" Error executing graph: {e}")
                break
            
            # ✅ Display results
            print(f"\n{'='*60}")
            print(f"ATTEMPT {retry_count + 1}/{max_retries}")
            print("=" * 60)
            print(f"Core Intent: {final_state.core_intent}")
            print(f"Context: {final_state.context_notes}")
            print(f"Developer Task: {final_state.developer_task}")
            print(f"Satisfied: {final_state.is_satisfied}")
            
            if not final_state.is_satisfied:
                print("Suggestions:")
                for s in final_state.suggestions:
                    print(f"- {s}")
                break  # End if query enhancement fails
            else:
                # Show Master Planner results
                print(f"Master Planner Success: {final_state.master_planner_success}")
                print(f"Master Planner Message: {final_state.master_planner_message}")
                
                if final_state.master_planner_success:
                    # ✅ SUCCESS: Show files to modify and exit retry loop
                    if final_state.master_planner_result:
                        print(f"\n📊 SUMMARY")
                        print(f"Files to Modify ({len(final_state.master_planner_result)}):")
                        for i, file_info in enumerate(final_state.master_planner_result, 1):
                            print(f"  {i}. {file_info.file_path}")
                            print(f"     Priority: {file_info.priority}")
                            if hasattr(file_info, 'analysis') and hasattr(file_info.analysis, 'reason'):
                                print(f"     Reason: {file_info.analysis.reason}")
                        
                        # ✅ NEW: Print detailed plan
                        print_detailed_plan(final_state.master_planner_result)
                        
                    else:
                        print("No files identified for modification.")
                    break  # Success - exit retry loop
                else:
                    # ❌ FAILURE: Show why it failed and ask for clarification
                    print(f"\n Master Planner Failed (Attempt {retry_count + 1}/{max_retries})")
                    print(f"Reason: {final_state.master_planner_message}")
                    print("\nThis might be because:")
                    print("  • The specified file doesn't exist")
                    print("  • The task is too vague or abstract")
                    print("  • The project structure doesn't match the task")
                    
                    if retry_count < max_retries - 1:
                        # Ask for clarification
                        print(f"\n You have {max_retries - retry_count - 1} more attempts.")
                        clarification = input("Could you clarify your task or provide more details? (or 'skip' to continue): ").strip()
                        
                        if clarification.lower() in ['skip', 'continue', '']:
                            print("⏭ Skipping retry...")
                            break
                        elif clarification:
                            user_query = clarification  # Update query for next retry
                            # Save clarification to Redis and update history
                            save_to_history(current_user, clarification)
                            history.append(clarification)
                            print("🔄 Retrying with your clarification...")
                            retry_count += 1
                        else:
                            print("No clarification provided. Ending...")
                            break
                    else:
                        print("\n Maximum retry attempts reached.")
                        break
        
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())