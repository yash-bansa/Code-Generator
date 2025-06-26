from pyspark.sql import SparkSession
import pyspark

def load_data():
    """
    Load sample data using PySpark's data loading API.

    Returns:
        pyspark.sql.DataFrame: A DataFrame containing sample data.
    """
    spark = SparkSession.builder.appName('Sample Project').getOrCreate()
    df = spark.createDataFrame([(1, 'John', 90), (2, 'Jane', 70), (3, 'Bob', 95)], ['c_id', 'name', 'score'])
    return df

def run_pipeline():
    """
    Run the data processing pipeline using PySpark's DataFrame API.

    Returns:
        None
    """
    try:
        df = load_data()
        print("Data Loaded:")
        print(df)

        # Add processing logic
        df = df.withColumn('passed', df['score'] > 80)

        print("\nProcessed Data:")
        print(df)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_pipeline()