from pyspark.sql import SparkSession

def load_data():
    """
    Load data into a PySpark DataFrame.

    This function initializes a SparkSession, creates in-memory data,
    defines the schema, and loads the data into a PySpark DataFrame.

    Returns:
        pyspark.sql.DataFrame: A PySpark DataFrame containing the data.
    """
    try:
        # Initialize SparkSession
        spark = SparkSession.builder.appName("DataLoader").getOrCreate()
        
        # Create data in-memory
        data = [
            (1, "Alice", 95),
            (2, "Bob", 88),
            (3, "Charlie", 76)
        ]
        
        # Define schema
        schema = ["c_id", "name", "score"]
        
        # Create DataFrame
        df = spark.createDataFrame(data, schema)
        return df
    except Exception as e:
        # Handle any exceptions that occur during data loading
        print(f"An error occurred while loading data: {e}")
        raise