from pyspark.sql import SparkSession
from data_loader import load_data


def initialize_spark_session():
    """
    Initializes and returns a SparkSession for PySpark operations.

    Returns:
        SparkSession: A SparkSession object for managing the PySpark environment.
    """
    try:
        return SparkSession.builder.appName("StudentPipeline").getOrCreate()
    except Exception as e:
        raise RuntimeError("Failed to initialize SparkSession") from e


def run_pipeline():
    """
    Runs the data processing pipeline using PySpark.

    This function initializes a SparkSession, loads data, processes it to add a
    "passed" column based on the "score" column, and displays the results.
    """
    try:
        # Initialize SparkSession
        spark = initialize_spark_session()

        # Load data using PySpark
        df = spark.read.json("./examples/sample_project/data_loader.py")
        print("Data Loaded:")
        df.show()

        # Add processing logic
        from pyspark.sql.functions import col, when

        # Add a "passed" column based on the "score" column
        df = df.withColumn("passed", when(col("score") > 80, True).otherwise(False))

        print("\nProcessed Data:")
        df.show()

    except Exception as e:
        print(f"An error occurred during pipeline execution: {e}")
    finally:
        # Stop the SparkSession to release resources
        if 'spark' in locals():
            spark.stop()


if __name__ == "__main__":
    run_pipeline()