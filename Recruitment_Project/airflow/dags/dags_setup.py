from airflow import DAG
from airflow.operators.python_operator import PythonOperator
import ETL_Cassandra_S3
from create_redshift import *
import datetime

with DAG(
    dag_id='ETL_cassandra_s3_dag',
    start_date=datetime.datetime(2023, 9, 3),
    schedule_interval='*/5 * * * *'
) as dag:
    main_process = ETL_Cassandra_S3.main_process()
    
    create_redshift = PythonOperator(
        task_id='create_redshift_schema_and_copy_data_to_redshift',
        python_callable=create_redshift_schema
    )
    
    Extract = PythonOperator(
        task_id='extract_data_from_cassandra',
        python_callable=main_process.extract_data_from_cassandra,
    )

    process_click_data = PythonOperator(
        task_id='process_click_data',
        python_callable=main_process.process_click_data,
        op_args=[Extract.output]
    )

    process_conversion_data = PythonOperator(
        task_id='process_conversion_data',
        python_callable=main_process.process_conversion_data,
        op_args=[Extract.output]
    )

    process_qualified_data = PythonOperator(
        task_id='process_qualified_data',
        python_callable=main_process.process_qualified_data,
        op_args=[Extract.output]
    )

    process_unqualified_data = PythonOperator(
        task_id='process_unqualified_data',
        python_callable=main_process.process_unqualified_data,
        op_args=[Extract.output]
    )
    Transform = PythonOperator(
        task_id='Transform_data',
        python_callable=main_process.process_result,
        op_args=[process_click_data.output, process_conversion_data.output,
                 process_qualified_data.output, process_unqualified_data.output]
    )

    Load = PythonOperator(
        task_id='Load_data_to_s3',
        python_callable=main_process.write_data_to_s3,
        op_args=[Transform.output]
    )

    
    create_redshift >> Extract >> [process_click_data, process_conversion_data, process_qualified_data, process_unqualified_data] >> Transform >> Load 
