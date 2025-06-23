#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent import SQLGeneratorAgent
from src.utils import QueryFormatter

def main():
    """Main function to run the SQL Generator Agent"""
    print("🤖 SQL Generator Agent with LM Studio")
    print("=" * 50)
    
    # Initialize the agent
    agent = SQLGeneratorAgent()
    
    # Display schema information
    print("\n📋 Database Schema:")
    print("-" * 30)
    schema = agent.get_schema_info()
    print(schema)
    print("-" * 30)
    
    print("\n💡 Example queries you can try:")
    print("- Show me all users")
    print("- Find the average age of users")
    print("- Get users who are older than 25")
    print("- Count how many orders each user has made")
    print("- Show me the most expensive products")
    
    while True:
        print("\n" + "=" * 50)
        user_input = input("\n🗣️  Enter your query (or 'quit' to exit): ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
        
        if not user_input:
            print("❌ Please enter a valid query.")
            continue
        
        # Process the query
        result = agent.process_query(user_input)
        
        # Display results
        print("\n" + "=" * 50)
        print("🎯 RESULTS")
        print("=" * 50)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"📝 Analysis: {result.get('analysis', 'N/A')[:200]}...")
            print(f"\n🔧 Generated SQL: {result.get('sql_query', 'N/A')}")
            print(f"\n✅ Validation: {result.get('validation_result', 'N/A')}")
            
            if result.get('execution_result'):
                print(f"\n📊 Query Results:")
                formatted_results = QueryFormatter.format_results(result['execution_result'])
                print(formatted_results)
            
            if result.get('final_response'):
                print(f"\n🤖 Explanation:")
                print(result['final_response'])
            
            if result.get('errors'):
                print(f"\n⚠️  Warnings:")
                for error in result['errors']:
                    print(f"  - {error}")

def test_connection():
    """Test connections to LM Studio and database"""
    print("🔍 Testing connections...")
    
    from src.lm_studio_client import LMStudioClient
    from src.database import DatabaseManager
    
    # Test LM Studio connection
    llm_client = LMStudioClient()
    if llm_client.check_connection():
        print("✅ LM Studio connection: OK")
    else:
        print("❌ LM Studio connection: FAILED")
        print("   Make sure LM Studio is running with a loaded model")
    
    # Test database connection
    db_manager = DatabaseManager()
    if db_manager.connect():
        print("✅ Database connection: OK")
        db_manager.disconnect()
    else:
        print("❌ Database connection: FAILED")
        print("   Check your database path in .env file")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_connection()
    else:
        main()