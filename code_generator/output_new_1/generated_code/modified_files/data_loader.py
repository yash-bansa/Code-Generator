from pyspark.sql import SparkSession
import pandas as pd

def create_spark_session():
    """
    Create a PySpark SparkSession instance for data processing.

    Returns:
        SparkSession: A SparkSession instance.
    """
    return SparkSession.builder.appName('DataLoader').getOrCreate()


def load_data():
    """
    Load data from a simulated CSV or database.

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
        spark = create_spark_session()
        df = spark.createDataFrame(data)
        return df
    except Exception as e:
        print(f"An error occurred: {e}")
        return None