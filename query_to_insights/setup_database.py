#!/usr/bin/env python3

import sqlite3
import os

def setup_database(db_path="examples/sample.db"):
    """Create and populate the sample SQLite database"""
    
    # Create the examples directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🗑️ Removed existing database")
    
    # Create new database
    print(f"🏗️ Creating database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    print("📋 Creating tables...")
    
    # Users table
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
    
    # Products table
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price DECIMAL(10, 2),
            category TEXT,
            stock_quantity INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Orders table
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            total_amount DECIMAL(10, 2),
            order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    # Insert sample data
    print("📊 Inserting sample data...")
    
    # Users data
    users_data = [
        (1, 'Alice Johnson', 'alice@email.com', 28, 'New York'),
        (2, 'Bob Smith', 'bob@email.com', 34, 'Los Angeles'),
        (3, 'Carol Davis', 'carol@email.com', 22, 'Chicago'),
        (4, 'David Wilson', 'david@email.com', 45, 'Houston'),
        (5, 'Eva Brown', 'eva@email.com', 31, 'Phoenix'),
        (6, 'Frank Miller', 'frank@email.com', 29, 'Philadelphia'),
        (7, 'Grace Lee', 'grace@email.com', 26, 'San Antonio'),
        (8, 'Henry Taylor', 'henry@email.com', 38, 'San Diego')
    ]
    
    cursor.executemany("""
        INSERT INTO users (id, name, email, age, city) VALUES (?, ?, ?, ?, ?)
    """, users_data)
    
    # Products data
    products_data = [
        (1, 'MacBook Pro', 1299.99, 'Electronics', 25),
        (2, 'iPhone 15', 799.99, 'Electronics', 50),
        (3, 'Coffee Maker Deluxe', 129.99, 'Appliances', 30),
        (4, 'Python Programming Book', 49.99, 'Books', 100),
        (5, 'Wireless Headphones', 199.99, 'Electronics', 40),
        (6, 'Smart Watch', 349.99, 'Electronics', 35),
        (7, 'Desk Chair', 299.99, 'Furniture', 20),
        (8, 'LED Monitor', 249.99, 'Electronics', 45),
        (9, 'Bluetooth Speaker', 89.99, 'Electronics', 60),
        (10, 'Kitchen Blender', 79.99, 'Appliances', 25)
    ]
    
    cursor.executemany("""
        INSERT INTO products (id, name, price, category, stock_quantity) VALUES (?, ?, ?, ?, ?)
    """, products_data)
    
    # Orders data
    orders_data = [
        (1, 1, 1, 1, 1299.99, 'completed'),   # Alice bought MacBook Pro
        (2, 1, 4, 2, 99.98, 'completed'),     # Alice bought 2 Books
        (3, 2, 2, 1, 799.99, 'completed'),    # Bob bought iPhone
        (4, 3, 3, 1, 129.99, 'pending'),      # Carol bought Coffee Maker
        (5, 4, 5, 1, 199.99, 'completed'),    # David bought Headphones
        (6, 5, 4, 3, 149.97, 'completed'),    # Eva bought 3 Books
        (7, 2, 1, 1, 1299.99, 'pending'),     # Bob bought MacBook Pro
        (8, 3, 2, 1, 799.99, 'completed'),    # Carol bought iPhone
        (9, 6, 6, 1, 349.99, 'completed'),    # Frank bought Smart Watch
        (10, 7, 8, 2, 499.98, 'pending'),     # Grace bought 2 Monitors
        (11, 8, 9, 1, 89.99, 'completed'),    # Henry bought Speaker
        (12, 1, 5, 1, 199.99, 'completed'),   # Alice bought Headphones
        (13, 4, 7, 1, 299.99, 'pending'),     # David bought Chair
        (14, 5, 10, 1, 79.99, 'completed'),   # Eva bought Blender
        (15, 2, 6, 1, 349.99, 'completed')    # Bob bought Smart Watch
    ]
    
    cursor.executemany("""
        INSERT INTO orders (id, user_id, product_id, quantity, total_amount, status) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, orders_data)
    
    # Commit and close
    conn.commit()
    conn.close()
    
    print(f"✅ Database setup complete!")
    print(f"📍 Location: {os.path.abspath(db_path)}")
    print(f"📊 Data summary:")
    print(f"   - {len(users_data)} users")
    print(f"   - {len(products_data)} products")
    print(f"   - {len(orders_data)} orders")
    
    return db_path

def show_database_info(db_path="examples/sample.db"):
    """Display information about the database"""
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"\n📋 Database Schema for: {db_path}")
    print("=" * 50)
    
    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n📊 Table: {table_name}")
        print("-" * 30)
        
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"  → {count} rows")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "info":
            show_database_info()
        elif sys.argv[1] == "setup":
            setup_database()
            show_database_info()
    else:
        setup_database()
        show_database_info()