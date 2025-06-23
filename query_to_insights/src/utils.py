from typing import Dict, Any

class PromptTemplates:
    """SQL generation prompt templates"""
    
    ANALYZE_QUERY_PROMPT = """
    You are an expert SQL analyst. Analyze the following natural language query and extract key information.
    
    Database Schema:
    {schema}
    
    User Query: {user_query}
    
    Please analyze this query and provide:
    1. What tables are likely needed
    2. What columns are mentioned or implied
    3. What type of operation (SELECT, INSERT, UPDATE, DELETE)
    4. Any filtering conditions
    5. Any aggregations or groupings needed
    
    Respond in a structured format.
    """
    
    GENERATE_SQL_PROMPT = """
    You are an expert SQL developer. Generate a SQL query based on the analysis and requirements.
    
    Database Schema:
    {schema}
    
    User Request: {user_query}
    
    Analysis: {analysis}
    
    Generate a SQL query that fulfills the user's request. 
    
    Rules:
    - Only use tables and columns that exist in the schema
    - Use proper SQL syntax
    - Include comments if the query is complex
    - Return ONLY the SQL query, no explanation
    
    SQL Query:
    """
    
    VALIDATE_SQL_PROMPT = """
    You are a SQL validator. Review the following SQL query for correctness.
    
    Database Schema:
    {schema}
    
    SQL Query: {sql_query}
    
    Check for:
    1. Syntax errors
    2. Non-existent tables or columns
    3. Logic errors
    4. Potential performance issues
    
    Respond with:
    - "VALID" if the query is correct
    - "INVALID: [reason]" if there are issues
    - Suggestions for improvement if needed
    """
    
    EXPLAIN_RESULTS_PROMPT = """
    You are a data analyst. Explain the following SQL query results in natural language.
    
    Original Query: {user_query}
    SQL Query: {sql_query}
    Results: {results}
    
    Provide a clear, concise explanation of what the results show.
    """

class QueryFormatter:
    """Utility class for formatting queries and results"""
    
    @staticmethod
    def format_results(results: list) -> str:
        """Format query results for display"""
        if not results:
            return "No results found."
        
        if isinstance(results[0], dict) and "error" in results[0]:
            return f"Error: {results[0]['error']}"
        
        # Format as a simple table
        if len(results) == 1:
            return str(results[0])
        
        # For multiple results, format as a list
        formatted = []
        for i, result in enumerate(results[:10]):  # Limit to first 10 results
            formatted.append(f"Row {i+1}: {result}")
        
        if len(results) > 10:
            formatted.append(f"... and {len(results) - 10} more rows")
        
        return "\n".join(formatted)
    
    @staticmethod
    def clean_sql_query(query: str) -> str:
        """Clean and format SQL query"""
        # Remove extra whitespace and comments
        lines = query.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('--'):
                cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines)
    
    @staticmethod
    def extract_sql_from_response(response: str) -> str:
        """Extract SQL query from LLM response"""
        # Look for SQL keywords to find the actual query
        lines = response.split('\n')
        sql_lines = []
        
        in_sql_block = False
        for line in lines:
            line = line.strip()
            
            # Check if line starts with SQL keywords
            if any(line.upper().startswith(keyword) for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']):
                in_sql_block = True
            
            if in_sql_block:
                if line and not line.startswith('#') and not line.startswith('--'):
                    sql_lines.append(line)
                elif line == '' and sql_lines:
                    break
        
        if sql_lines:
            return ' '.join(sql_lines)
        
        # If no clear SQL found, return the whole response cleaned
        return QueryFormatter.clean_sql_query(response)

class AgentState:
    """State management for the agent"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.user_query = ""
        self.analysis = ""
        self.sql_query = ""
        self.validation_result = ""
        self.execution_result = []
        self.final_response = ""
        self.iteration_count = 0
        self.errors = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_query": self.user_query,
            "analysis": self.analysis,
            "sql_query": self.sql_query,
            "validation_result": self.validation_result,
            "execution_result": self.execution_result,
            "final_response": self.final_response,
            "iteration_count": self.iteration_count,
            "errors": self.errors
        }