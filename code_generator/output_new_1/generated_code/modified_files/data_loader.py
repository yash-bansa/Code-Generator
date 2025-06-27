from pyspark.sql import SparkSession
import pandas as pd  # Not used anymore, consider removing this import

def load_data():
    """
    Load data from a simulated CSV or database using PySpark's SparkSession.

    Returns:
        spark_df (pyspark.sql.dataframe.DataFrame): A DataFrame containing the loaded data.
    """
    try:
        # Simulate loading data from a CSV or database
        data = {
            "c_id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "score": [95, 88, 76]
        }
        spark = SparkSession.builder.appName('data_loader').getOrCreate()
        df = spark.createDataFrame(data)
        return df
    except Exception as e:
        print(f"An error occurred: {e}")
        return None