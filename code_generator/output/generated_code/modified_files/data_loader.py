from pyspark.sql import SparkSession
from pyspark.sql.functions import lit

def load_data(spark_session):
    """
    Load data from a simulated source and add a 'rank' column.

    Args:
        spark_session (SparkSession): The SparkSession to use for creating the DataFrame.

    Returns:
        DataFrame: A Spark DataFrame with the loaded data and a 'rank' column.
    """
    try:
        df = spark_session.createDataFrame([
            {'c_id': 1, 'name': 'Alice', 'score': 95},
            {'c_id': 2, 'name': 'Bob', 'score': 88},
            {'c_id': 3, 'name': 'Charlie', 'score': 76}
        ]).withColumn('rank', lit(1))
        return df
    except Exception as e:
        print(f"An error occurred: {e}")
        return None