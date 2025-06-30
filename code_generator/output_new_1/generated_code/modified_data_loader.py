from pyspark.sql import SparkSession
import pandas as pd

def load_data(spark_session):
    """
    Load data from a simulated CSV or database.

    Args:
        spark_session (SparkSession): The SparkSession instance for ETL data processing.

    Returns:
        DataFrame: A PySpark DataFrame containing the loaded data.
    """
    try:
        # Simulate loading data from a CSV or database
        data = {
            "c_id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "score": [95, 88, 76]
        }
        df = spark_session.createDataFrame(data)
        return df
    except Exception as e:
        print(f"An error occurred: {e}")
        return None