from data_loader import load_data
from pyspark.sql import SparkSession

def run_pipeline():
    """
    Run the data pipeline using PySpark.

    This function loads data, processes it, and prints the results.
    """
    spark = SparkSession.builder.appName('Sample Pipeline').getOrCreate()
    df = spark.createDataFrame(load_data())
    print("Data Loaded:")
    print(df)

    # Add processing logic
    df = df.withColumn('passed', df['score'] > 80)

    print("\nProcessed Data:")
    print(df)

if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print(f"An error occurred: {e}")