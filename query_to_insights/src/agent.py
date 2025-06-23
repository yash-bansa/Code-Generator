from langgraph.graph import StateGraph, END
from typing import Dict, Any
import os
from dotenv import load_dotenv

from .lm_studio_client import LMStudioClient
from .database import DatabaseManager
from .utils import PromptTemplates, QueryFormatter, AgentState

load_dotenv()

class SQLGeneratorAgent:
    def __init__(self):
        self.llm_client = LMStudioClient()
        self.db_manager = DatabaseManager()
        self.prompts = PromptTemplates()
        self.formatter = QueryFormatter()
        self.max_iterations = int(os.getenv("MAX_ITERATIONS", 5))
        
        # Initialize the graph
        self.graph = self._create_graph()
    
    def _create_graph(self):
        """Create the LangGraph workflow"""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("analyze_query", self.analyze_query_node)
        workflow.add_node("generate_sql", self.generate_sql_node)
        workflow.add_node("validate_sql", self.validate_sql_node)
        workflow.add_node("execute_sql", self.execute_sql_node)
        workflow.add_node("explain_results", self.explain_results_node)
        
        # Define the flow
        workflow.set_entry_point("analyze_query")
        workflow.add_edge("analyze_query", "generate_sql")
        workflow.add_edge("generate_sql", "validate_sql")
        workflow.add_conditional_edges(
            "validate_sql",
            self.should_retry,
            {
                "retry": "generate_sql",
                "execute": "execute_sql"
            }
        )
        workflow.add_edge("execute_sql", "explain_results")
        workflow.add_edge("explain_results", END)
        
        return workflow.compile()
    
    def analyze_query_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the user's natural language query"""
        print("🔍 Analyzing query...")
        
        schema = self.db_manager.get_schema()
        prompt = self.prompts.ANALYZE_QUERY_PROMPT.format(
            schema=schema,
            user_query=state["user_query"]
        )
        
        try:
            analysis = self.llm_client.generate_response(prompt)
            state["analysis"] = analysis
            print(f"Analysis: {analysis[:100]}...")
        except Exception as e:
            state["errors"].append(f"Analysis error: {str(e)}")
            state["analysis"] = "Error in analysis"
        
        return state
    
    def generate_sql_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SQL query based on analysis"""
        print("🛠️ Generating SQL...")
        
        schema = self.db_manager.get_schema()
        prompt = self.prompts.GENERATE_SQL_PROMPT.format(
            schema=schema,
            user_query=state["user_query"],
            analysis=state["analysis"]
        )
        
        try:
            sql_response = self.llm_client.generate_response(prompt)
            sql_query = self.formatter.extract_sql_from_response(sql_response)
            state["sql_query"] = sql_query
            print(f"Generated SQL: {sql_query}")
        except Exception as e:
            state["errors"].append(f"SQL generation error: {str(e)}")
            state["sql_query"] = ""
        
        return state
    
    def validate_sql_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the generated SQL query"""
        print("✅ Validating SQL...")
        
        if not state["sql_query"]:
            state["validation_result"] = "INVALID: No SQL query generated"
            return state
        
        # Technical validation using database
        is_valid, db_message = self.db_manager.validate_query(state["sql_query"])
        
        if is_valid:
            # Additional LLM validation for logic
            schema = self.db_manager.get_schema()
            prompt = self.prompts.VALIDATE_SQL_PROMPT.format(
                schema=schema,
                sql_query=state["sql_query"]
            )
            
            try:
                llm_validation = self.llm_client.generate_response(prompt)
                if "VALID" in llm_validation.upper():
                    state["validation_result"] = "VALID"
                else:
                    state["validation_result"] = llm_validation
            except Exception as e:
                state["validation_result"] = f"VALID (DB), LLM validation error: {str(e)}"
        else:
            state["validation_result"] = f"INVALID: {db_message}"
        
        print(f"Validation: {state['validation_result']}")
        return state
    
    def should_retry(self, state: Dict[str, Any]) -> str:
        """Decide whether to retry SQL generation or proceed to execution"""
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        
        if (state["validation_result"].startswith("INVALID") and 
            state["iteration_count"] < self.max_iterations):
            print(f"🔄 Retrying (attempt {state['iteration_count']})...")
            return "retry"
        else:
            return "execute"
    
    def execute_sql_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the SQL query"""
        print("🚀 Executing SQL...")
        
        if not state["sql_query"] or state["validation_result"].startswith("INVALID"):
            state["execution_result"] = [{"error": "Cannot execute invalid query"}]
            return state
        
        try:
            results, success = self.db_manager.execute_query(state["sql_query"])
            state["execution_result"] = results
            
            if success:
                print(f"Execution successful: {len(results)} results")
            else:
                print(f"Execution failed: {results}")
                
        except Exception as e:
            state["execution_result"] = [{"error": str(e)}]
            state["errors"].append(f"Execution error: {str(e)}")
        
        return state
    
    def explain_results_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Explain the results in natural language"""
        print("📝 Explaining results...")
        
        formatted_results = self.formatter.format_results(state["execution_result"])
        prompt = self.prompts.EXPLAIN_RESULTS_PROMPT.format(
            user_query=state["user_query"],
            sql_query=state["sql_query"],
            results=formatted_results
        )
        
        try:
            explanation = self.llm_client.generate_response(prompt)
            state["final_response"] = explanation
            print("Explanation generated")
        except Exception as e:
            state["final_response"] = f"Results: {formatted_results}\n\nNote: Could not generate explanation due to: {str(e)}"
            state["errors"].append(f"Explanation error: {str(e)}")
        
        return state
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a user query through the entire workflow"""
        print(f"\n🎯 Processing query: {user_query}")
        
        # Check connections
        if not self.llm_client.check_connection():
            return {
                "error": "Cannot connect to LM Studio. Please ensure it's running on the configured port.",
                "user_query": user_query
            }
        
        if not self.db_manager.connect():
            return {
                "error": "Cannot connect to database.",
                "user_query": user_query
            }
        
        # Initialize state
        initial_state = {
            "user_query": user_query,
            "analysis": "",
            "sql_query": "",
            "validation_result": "",
            "execution_result": [],
            "final_response": "",
            "iteration_count": 0,
            "errors": []
        }
        
        try:
            # Run the workflow
            final_state = self.graph.invoke(initial_state)
            return final_state
        except Exception as e:
            return {
                "error": f"Workflow error: {str(e)}",
                "user_query": user_query
            }
        finally:
            self.db_manager.disconnect()
    
    def get_schema_info(self) -> str:
        """Get database schema information"""
        if self.db_manager.connect():
            schema = self.db_manager.get_schema()
            self.db_manager.disconnect()
            return schema
        return "Could not retrieve schema"