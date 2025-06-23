from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('DataLoader').getOrCreate()
from pyspark.sql.functions import col, row_number
from pyspark.sql.window import Window

def load_data() -> None:
    """
    Load data from CSV file using PySpark and add 'rank' column.

    :return: None
    """
    df = spark.read.csv('./examples/sample_project/data_loader.py', header=True, inferSchema=True)
    df = df.withColumn('rank', row_number().over(Window.partitionBy('c_id').rowsBetween(Window.unboundedPreceding, Window.currentRow)))
    return df

def run_pipeline() -> None:
    """
    Run the data pipeline.

    :return: None
    """
    try:
        df = load_data()
        print("Data Loaded:")
        print(df)

        # Add processing logic
        df = df.withColumn("passed", col("score") > 80)

        print("\nProcessed Data:")
        print(df)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_pipeline()