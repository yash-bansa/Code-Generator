from data_loader import load_data
from pyspark.sql import SparkSession

def create_spark_session():
    """
    Create a SparkSession for ETL data processing.

    Returns:
        SparkSession: A SparkSession instance.
    """
    return SparkSession.builder.appName('ETL Pipeline').getOrCreate()

def run_pipeline():
    """
    Run the ETL pipeline using PySpark.
    """
    try:
        spark = create_spark_session()
        df = spark.createDataFrame(load_data())
        
        print("Data Loaded:")
        print(df.toPandas())  # Convert to pandas DataFrame for printing
        
        # Add processing logic
        df = df.withColumn('passed', df['score'] > 80)
        
        print("\nProcessed Data:")
        print(df.toPandas())  # Convert to pandas DataFrame for printing
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_pipeline()