from pyspark.sql import SparkSession
from data_loader import load_data

def create_spark_session():
    """
    Create a SparkSession instance for data processing.

    Returns:
        SparkSession: A SparkSession instance.
    """
    return SparkSession.builder.appName('Sample Pipeline').getOrCreate()

def load_data(spark_session):
    """
    Load data from a CSV file using PySpark's SparkSession.

    Args:
        spark_session (SparkSession): A SparkSession instance.

    Returns:
        DataFrame: A PySpark DataFrame containing the loaded data.
    """
    return spark_session.read.csv('./examples/sample_project/data_loader.py', header=True, inferSchema=True)

def run_pipeline():
    """
    Run the data processing pipeline using PySpark's DataFrame API.
    """
    try:
        spark_session = create_spark_session()
        df = load_data(spark_session)
        print("Data Loaded:")
        df.show()

        # Add processing logic
        df = df.withColumn("passed", df["score"] > 80)

        print("\nProcessed Data:")
        df.show()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_pipeline()