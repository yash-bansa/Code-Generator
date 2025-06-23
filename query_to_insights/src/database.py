import sqlite3
from typing import List, Dict, Any, Tuple
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.getenv("DATABASE_PATH", "./examples/sample.db")
        self.connection = None
    
    def connect(self):
        """Connect to the database"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            return True
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def get_schema(self) -> str:
        """Get database schema information"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            schema_info = []
            for table in tables:
                table_name = table[0]
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                column_info = []
                for col in columns:
                    column_info.append(f"{col[1]} {col[2]}")
                
                schema_info.append(f"Table: {table_name}\nColumns: {', '.join(column_info)}")
            
            return "\n\n".join(schema_info)
            
        except sqlite3.Error as e:
            return f"Error retrieving schema: {e}"
    
    def execute_query(self, query: str) -> Tuple[List[Dict[str, Any]], bool]:
        """Execute SQL query and return results"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Check if it's a SELECT query
            if query.strip().upper().startswith('SELECT'):
                results = []
                for row in cursor.fetchall():
                    results.append(dict(row))
                return results, True
            else:
                # For INSERT, UPDATE, DELETE
                self.connection.commit()
                return [{"affected_rows": cursor.rowcount}], True
                
        except sqlite3.Error as e:
            return [{"error": str(e)}], False
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate SQL query without executing it"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            # Use EXPLAIN to validate without executing
            cursor.execute(f"EXPLAIN {query}")
            return True, "Query is valid"
        except sqlite3.Error as e:
            return False, str(e)
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample data from a table"""
        if not self.connection:
            self.connect()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            return results
        except sqlite3.Error as e:
            return [{"error": str(e)}]