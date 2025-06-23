# SQL Generator Agent with LM Studio

A LangGraph-based SQL generator agent that uses LM Studio for natural language to SQL conversion.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup LM Studio

1. Download and install [LM Studio](https://lmstudio.ai/)
2. Load a code-capable model (e.g., CodeLlama, Mistral, or similar)
3. Start the local server:
   - In LM Studio, go to "Local Server" tab
   - Click "Start Server"
   - Default URL: `http://localhost:1234`

### 3. Create SQLite Database

You have several options:

#### Option A: Use the setup script (Recommended)
```bash
python setup_database.py
```

#### Option B: Use the example script
```bash
python examples/example.py
```

#### Option C: Manual creation
```python
import sqlite3

# Create database
conn = sqlite3.connect('examples/sample.db')
cursor = conn.cursor()

# Create your tables here
cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        age INTEGER
    )
""")

# Insert sample data
cursor.execute("INSERT INTO users (name, email, age) VALUES (?, ?, ?)", 
               ("John Doe", "john@email.com", 30))

conn.commit()
conn.close()
```

### 4. Configure Environment

Edit the `.env` file:
```bash
# LM Studio Configuration
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio

# Database Configuration  
DATABASE_PATH=./examples/sample.db

# Agent Configuration
MAX_ITERATIONS=5
TEMPERATURE=0.1
```

## Usage

### Test Connections
```bash
python main.py test
```

### Run the Agent
```bash
python main.py
```

### Example Queries
Once running, try these natural language queries:
- "Show me all users"
- "Find users older than 30"
- "What products are in the Electronics category?"
- "Show me the total sales for each user"
- "Which product has the highest price?"

## How It Works

The agent uses a LangGraph workflow with these steps:

1. **Analyze Query**: Understands the natural language request
2. **Generate SQL**: Creates SQL query based on database schema
3. **Validate SQL**: Checks syntax and logic
4. **Execute SQL**: Runs the query against the database
5. **Explain Results**: Provides natural language explanation

## Project Structure

```
sql-generator-agent/
├── main.py                 # Main entry point
├── setup_database.py       # Database setup script
├── requirements.txt        # Python dependencies
├── .env                   # Environment configuration
├── src/
│   ├── agent.py           # LangGraph agent implementation
│   ├── lm_studio_client.py # LM Studio API client
│   ├── database.py        # Database management
│   └── utils.py           # Utilities and prompts
└── examples/
    ├── example.py         # Example usage
    └── sample.db          # Sample SQLite database
```

## Troubleshooting

### LM Studio Connection Issues
- Ensure LM Studio is running with a model loaded
- Check if the server is listening on `http://localhost:1234`
- Verify the model can handle code generation tasks

### Database Issues
- Make sure the database file exists at the specified path
- Check file permissions
- Verify the database has tables and data

### Query Issues
- Start with simple queries
- Ensure your natural language is clear and specific
- Check that referenced tables/columns exist in your database

## Customization

### Adding New Database Types
Modify `src/database.py` to support other databases:
```python
# Add support for PostgreSQL, MySQL, etc.
import psycopg2  # for PostgreSQL
import mysql.connector  # for MySQL
```

### Custom Prompts
Edit prompts in `src/utils.py` to improve query generation for your specific use case.

### Different Models
The agent works with any OpenAI-compatible API. Update the base URL in `.env` to use different providers.

## Sample Database Schema

The setup script creates a sample e-commerce database with:

- **users**: Customer information (id, name, email, age, city)
- **products**: Product catalog (id, name, price, category, stock)
- **orders**: Order history (id, user_id, product_id, quantity, total_amount, status)

## Contributing

Feel free to submit issues and enhancement requests!