import pyspark
from pyspark.sql import SparkSession

def run_pipeline():
    """
    Run the data pipeline using PySpark.
    
    This function loads data, applies transformation logic, and outputs the result.
    """
    spark = SparkSession.builder.appName('Sample Pipeline').getOrCreate()
    try:
        df = spark.createDataFrame(load_data())
        
        print("Data Loaded:")
        df.select('c_id', 'name', 'score', 'passed').write.format('console').option('truncate', 'false').save()
        
        # Add processing logic
        df = df.withColumn('passed', df['score'] > 80)
        
        print("\nProcessed Data:")
        df.select('c_id', 'name', 'score', 'passed').write.format('console').option('truncate', 'false').save()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_pipeline()