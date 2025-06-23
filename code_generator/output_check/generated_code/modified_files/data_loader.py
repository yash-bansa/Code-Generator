from pyspark.sql import SparkSession

def load_data():
    """
    Load data from a simulated data source and return a PySpark DataFrame.

    Returns:
    spark.DataFrame: A DataFrame containing the loaded data.
    """
    spark = SparkSession.builder.appName('DataLoader').getOrCreate()
    data = {
        "c_id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "score": [95, 88, 76],
        "rank": [1, 2, 3]
    }
    df = spark.createDataFrame(data)
    return df