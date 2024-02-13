import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from uuid import *
import time_uuid
class main_process:
    def __init__(self):
        self.gen_latest = '2000-01-01 00:00:00'
        self.scala_version = '2.12'
        self.spark_version = '3.0.1'
        packages = [
            'com.datastax.spark:spark-cassandra-connector_2.12:3.0.1',
            "com.amazonaws:aws-java-sdk-s3:1.12.526",
            "org.apache.hadoop:hadoop-aws:2.7.4",
        ]
        self.spark = SparkSession.builder\
            .master("local")\
            .config("spark.jars.packages", ",".join(packages))\
            .getOrCreate()

        self.spark._jsc.hadoopConfiguration().set(
            "fs.s3a.awsAccessKeyId", "**********")
        self.spark._jsc.hadoopConfiguration().set(
            "fs.s3a.awsSecretAccessKey", "**********")
        self.spark._jsc.hadoopConfiguration().set(
            "fs.s3a.impl", "org.apache.hadoop.fs.s3native.NativeS3FileSystem")

    def process_timeuuid(self, df):
        spark_time = df.select('create_time').collect()
        normal_time = []
        for i in range(len(spark_time)):
            a = time_uuid.TimeUUID(bytes=UUID(
                spark_time[i][0]).bytes).get_datetime().strftime('%Y-%m-%d %H:%M:%S')
            normal_time.append(a)
        spark_timeuuid = []
        for i in range(len(spark_time)):
            spark_timeuuid.append(spark_time[i][0])
        time_data = self.spark.createDataFrame(
            zip(spark_timeuuid, normal_time), ['create_time', 'ts'])
        result = df.join(time_data, ['create_time'], 'inner').drop(df.ts)
        result = result.select('create_time', 'ts', 'bid', 'job_id',
                               'campaign_id', 'custom_track', 'group_id', 'publisher_id')
        result = result.withColumn("Date", to_date("ts")) \
            .withColumn("Hour", hour("ts"))
        return result

    def process_click_data(self, df):
        df = self.process_timeuuid(df)
        print('------------------Processing click data------------------')
        clicks_data = df.filter(df.custom_track == 'click')
        clicks_data = clicks_data.na.fill(0)
        cte1 = clicks_data.select("create_time", "ts", "Date", "Hour",
                                  "bid", "job_id", "campaign_id", "group_id", "publisher_id")
        clicks_output = cte1.groupBy("Date", "Hour", "job_id", "publisher_id", "campaign_id", "group_id") \
            .agg(sum("bid").alias("spend_hour"), count("create_time").alias("clicks"), avg("bid").alias("bid_set"))
        return clicks_output

    def process_conversion_data(self, df):
        df = self.process_timeuuid(df)
        print('------------------Processing conversion data------------------')
        conversions_data = df.filter(df.custom_track == 'conversion')
        conversions_data = conversions_data.na.fill(0)
        cte1 = conversions_data.select(
            "create_time", "ts", "Date", "Hour", "bid", "job_id", "campaign_id", "group_id", "publisher_id")
        conversions_output = cte1.groupBy("Date", "Hour", "job_id", "publisher_id", "campaign_id", "group_id") \
            .agg(count("create_time").alias("conversion"))
        return conversions_output

    def process_qualified_data(self, df):
        df = self.process_timeuuid(df)
        print('------------------Processing qualified data------------------')
        qualifieds_data = df.filter(df.custom_track == 'qualified')
        qualifieds_data = qualifieds_data.na.fill(0)
        cte1 = qualifieds_data.select(
            "create_time", "ts", "Date", "Hour", "bid", "job_id", "campaign_id", "group_id", "publisher_id")
        qualifieds_output = cte1.groupBy("Date", "Hour", "job_id", "publisher_id", "campaign_id", "group_id") \
            .agg(count("create_time").alias("qualified"))
        return qualifieds_output

    def process_unqualified_data(self, df):
        df = self.process_timeuuid(df)
        print('------------------Processing unqualified data------------------')
        unqualifieds_data = df.filter(df.custom_track == 'unqualified')
        unqualifieds_data = unqualifieds_data.na.fill(0)
        cte1 = unqualifieds_data.select(
            "create_time", "ts", "Date", "Hour", "bid", "job_id", "campaign_id", "group_id", "publisher_id")
        unqualifieds_output = cte1.groupBy("Date", "Hour", "job_id", "publisher_id", "campaign_id", "group_id") \
            .agg(count("create_time").alias("unqualified"))
        return unqualifieds_output

    def retrieve_company_data(self):
        company_data = self.spark.read \
            .format("jdbc") \
            .options(driver="com.mysql.cj.jdbc.Driver",
                     url="jdbc:mysql://localhost:3307/Study_Data_Engineer",
                     dbtable="job",
                     user="root",
                     password="admin") \
            .load()
        print('------------------Processing company data------------------')
        company_data = company_data.select("id", "company_id")
        company_data = company_data.withColumnRenamed("id", "job_id")
        return company_data

    def process_result(self, clicks_output, conversions_output, qualifieds_output, unqualifieds_output):
        print('------------------Processing cassandra data------------------')
        cassandra_output = clicks_output.join(conversions_output, ['job_id', 'publisher_id', 'campaign_id', 'group_id', 'Date', 'Hour'], 'full') \
            .join(qualifieds_output, ['job_id', 'publisher_id', 'campaign_id', 'group_id', 'Date', 'Hour'], 'full') \
            .join(unqualifieds_output, ['job_id', 'publisher_id', 'campaign_id', 'group_id', 'Date', 'Hour'], 'full')
        cassandra_output = cassandra_output.withColumn(
            "sources", lit("Cassandra"))
        
        company_data = self.retrieve_company_data()
        print('------------------Processing result data------------------')
        result = cassandra_output.join(
            company_data,
            cassandra_output['job_id'] == company_data['job_id'],
            'left'
        ).drop(company_data['job_id'])
        result = result.na.fill(0)
        return result

    def retrieve_cassandra_latest_time(self):
        df = self.spark.read.format("org.apache.spark.sql.cassandra").options(
            table="tracking", keyspace="Data_Engineering").load()
        df = self.process_timeuuid(df)
        cassandra_time = df.select("ts").orderBy(desc("ts")).collect()[0][0]
        if cassandra_time == None:
            cassandra_time = '2000-01-01 00:00:00'
        return cassandra_time

    def write_data_to_s3(self, df):
        s3_bucket = "recruitment-project-tmph2003"
        s3_path = "s3a://" + s3_bucket + "/result.csv"
        df.coalesce(1).write \
            .format("csv") \
            .option("header", "true") \
            .mode("append") \
            .save(s3_path)

    def extract_data_from_cassandra(self):
        df = self.spark.read.format("org.apache.spark.sql.cassandra").options(
            table="tracking", keyspace="Data_Engineering").load().where(col("ts") > self.gen_latest)
        return df