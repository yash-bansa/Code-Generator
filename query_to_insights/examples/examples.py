#!/usr/bin/env python3

import sys
import os
import sqlite3

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import SQLGeneratorAgent

def create_sample_database():
    """Create a sample database for testing"""
    db_path = "examples/sample.db"
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            age INTEGER,
            city TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create products table
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price DECIMAL(10, 2),
            category TEXT,
            stock_quantity INTEGER
        )
    """)
    
    # Create orders table
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    # Insert sample data
    users_data = [
        (1, 'Alice Johnson', 'alice@email.com', 28, 'New York'),
        (2, 'Bob Smith', 'bob@email.com', 34, 'Los Angeles'),
        (3, 'Carol Davis', 'carol@email.com', 22, 'Chicago'),
        (4, 'David Wilson', 'david@email.com', 45, 'Houston'),
        (5, 'Eva Brown', 'eva@email.com', 31, 'Phoenix')
    ]
    
    cursor.executemany("""
        INSERT INTO users (id, name, email, age, city) VALUES (?, ?, ?, ?, ?)
    """, users_data)
    
    products_data = [
        (1, 'Laptop', 999.99, 'Electronics', 50),
        (2, 'Smartphone', 699.99, 'Electronics', 100),
        (3, 'Coffee Maker', 79.99, 'Appliances', 25),
        (4, 'Book', 19.99, 'Books', 200),
        (5, 'Headphones', 149.99, 'Electronics', 75)
    ]
    
    cursor.executemany("""
        INSERT INTO products (id, name, price, category, stock_quantity) VALUES (?, ?, ?, ?, ?)
    """, products_data)
    
    orders_data = [
        (1, 1, 1, 1),  # Alice bought 1 Laptop
        (2, 1, 4, 2),  # Alice bought 2 Books
        (3, 2, 2, 1),  # Bob bought 1 Smartphone
        (4, 3, 3, 1),  # Carol bought 1 Coffee Maker
        (5, 4, 5, 1),  # David bought 1 Headphones
        (6, 5, 4, 3),  # Eva bought 3 Books
        (7, 2, 1, 1),  # Bob bought 1 Laptop
        (8, 3, 2, 1)   # Carol bought 1 Smartphone
    ]
    
    cursor.executemany("""
        INSERT INTO orders (id, user_id, product_id, quantity) VALUES (?, ?, ?, ?)
    """, orders_data)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Sample database created at: {db_path}")
    return db_path

def run_example_queries():
    """Run some example queries"""
    print("\n🤖 Running example queries...")
    
    agent = SQLGeneratorAgent()
    
    example_queries = [
        "Show me all users",
        "Find users older than 30",
        "What products do we have in Electronics category?",
        "Show me all orders with user and product details",
        "Which user has made the most orders?"
    ]
    
    for query in example_queries:
        print(f"\n" + "="*60)
        print(f"Query: {query}")
        print("="*60)
        
        result = agent.process_query(query)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"🔧 SQL: {result.get('sql_query', 'N/A')}")
            if result.get('execution_result'):
                print(f"📊 Results: {len(result['execution_result'])} rows")
                # Show first few results
                for i, row in enumerate(result['execution_result'][:3]):
                    print(f"  Row {i+1}: {row}")
                if len(result['execution_result']) > 3:
                    print(f"  ... and {len(result['execution_result']) - 3} more rows")

if __name__ == "__main__":
    print("🗄️ Setting up sample database...")
    
    # Create the examples directory if it doesn't exist
    os.makedirs("examples", exist_ok=True)
    
    # Create sample database
    db_path = create_sample_database()
    
    # Run example queries
    run_example_queries()