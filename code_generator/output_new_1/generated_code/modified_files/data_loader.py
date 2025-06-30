from pyspark.sql import SparkSession
import pandas as pd

def load_data():
    """
    Load data from a simulated CSV or database and apply transformations.

    Returns:
        Spark DataFrame: Transformed data with a 'passed' column.
    """
    try:
        # Simulate loading data from a CSV or database
        data = {
            "c_id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "score": [95, 88, 76]
        }
        
        # Create a SparkSession for scalable data processing
        spark = SparkSession.builder.appName('DataLoader').getOrCreate()
        
        # Load data into a Spark DataFrame
        df = spark.createDataFrame(data)
        
        # Apply 'mark_passed_students' transformation using PySpark DataFrames
        df = df.withColumn('passed', df['score'] > 80)
        
        return df
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return None