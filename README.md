# Batch Processing : Data Pipeline for Recruitment Start Up

## Table of Contents

- [Batch Processing : Data Pipeline for Recruitment Start Up](#batch-processing--data-pipeline-for-recruitment-start-up)
  - [Table of Contents](#table-of-contents)
  - [1. Introduction](#1-introduction)
    - [Technologies used](#technologies-used)
  - [2. Implementation overview](#2-implementation-overview)
  - [3. Design](#3-design)
  - [4. Project Structure](#4-project-structure)
  - [5. Settings](#5-settings)
    - [Prerequisites](#prerequisites)
    - [Important note](#important-note)
    - [Running](#running)
  - [6. Implementation](#6-implementation)
    - [Import data from Input Data](#import-data-from-input-data)
    - [6.1 Generate recruitment data into Data Lake (Cassandra)](#61-generate-recruitment-data-into-data-lake-cassandra)
    - [6.2 DDL in Redshift](#62-ddl-in-redshift)
    - [6.3 Extract data from data lake](#63-extract-data-from-data-lake)
    - [6.4 Transform](#64-transform)
    - [6.5 Load data to Redshift](#65-load-data-to-redshift)
  - [7. Visualize result](#7-visualize-result)
    - [Visualization](#visualization)

## 1. Introduction

Data is collected from an start up company about their recruitment. We will build ETL pipelines which will transform raw data into actionable insights, store them in data lake (Cassandra), data warehouse (Mysql, Amazon Redshift) for enhanced data analytics capabilities.

### Technologies used

- Python
- Pyspark
- Cassandra
- Mysql
- Airflow
- AWS services : S3, Redshift (data warehouse)
- Docker
- Grafana

## 2. Implementation overview

Design data models for OLTP database (Cassandra) and data warehouse (MySQL, Amazon Redshift). Generate data from MySQL to Cassandra. Build an ETL pipeline to transform raw data from Cassandra and store them in S3 for staging. Then implement another ETL pipeline which process data from S3 and load them to Amazon Redshift for enhanced data analytics. Using Airflow to orchestrate pipeline workflow and Docker to containerize the project - allow for fast build, test, and deploy project.

<img src = assets/project_architect_overview.png alt = "Airflow conceptual view">

## 3. Design

<div style="display: grid; grid-template-columns: auto">
    <img src=assets/data_warehouse.png alt="Data model" width="600" height="500">
    <p> <b> <i> Data model for Data Warehouse </i> </b> </p>
</div>
<br> <br>
<div style="display: grid; grid-template-columns: auto">
  <img src=assets/airflow_workflow.png alt="Airflow Workflow" width="900px" height="300px">
  <p"> <b> <i> Airflow workflow </i> </b> </p>
</div>

## 4. Project Structure

```bash
Batch-Processing-Project
├── airflow
│   ├── dags
│   │   ├── create_redshift.py
│   │   ├── dags_setup.py
│   │   ├── ETL_Cassandra_S3.py
│   │   └── fake_data.py
│   └── logs
│       ├── dag_processor_manager
│       │   └── dag_processor_manager.log
│       └── scheduler
│           └── latest
├── assets
│   ├── airflow_workflow.png
│   ├── data_visualization.png
│   ├── data_warehouse.png
│   ├── ddl.png
│   ├── extract.png
│   ├── grafana_config.png
│   ├── load.png
│   ├── project_architect_overview.png
│   └── transform.png
├── docker-compose.yml
├── Input_Data
│   ├── data_cassandra
│   │   ├── search.csv
│   │   └── tracking.csv
│   └── data_mysql
│       ├── application.csv
│       ├── campaign.csv
│       ├── company.csv
│       ├── conversation.csv
│       ├── dev_user.csv
│       ├── events.csv
│       ├── group.csv
│       ├── job.csv
│       ├── job_location.csv
│       ├── master_city.csv
│       ├── master_major_category.csv
│       ├── master_minor_category.csv
│       ├── master_publisher.csv
│       ├── master_role.csv
│       ├── user_client_assignee.csv
│       └── user_role.csv
├── Makefile
├── README.md
├── requirements.txt
└── Transformed_Data
    └── Transformed_Data.csv

```

<br>

## 5. Settings

### Prerequisites

- AWS account
- AWS Services(S3, Redshift)
- Docker
- Airflow

### Important note

<b> You must specify AWS credentials for each of the following </b>

- S3 access : Create an IAM user "S3-admin" with <b> S3FullAccess </b>
- Redshift access : Create an IAM user "Redshift-admin" with <b> RedshiftFulAccess </b> policy

### Running

```
#Make must be installed first

# Start docker containers on your local computer
make up

# Add pip packages
make python
```

## 6. Implementation

### Import data from [Input Data](Input_Data/)

### 6.1 Generate recruitment data into Data Lake (Cassandra)
```bash
  python ./airflow/dags/fake_data.py
```

<b> [Generate data file](airflow/dags/fake_data.py) </b>
<br>

### 6.2 DDL in Redshift
<img src=assets/ddl.png weight="500px" height="250px">

<b> Airflow tasks </b>

```python
create_redshift = PythonOperator(
    task_id='create_redshift_schema_and_copy_data_to_redshift',
    python_callable=create_redshift_schema
)
```

### 6.3 Extract data from data lake
<img src=assets/extract.png weight="500px" height="250px">

<b> Airflow tasks </b>

```python
Extract = PythonOperator(
    task_id='extract_data_from_cassandra',
    python_callable=main_process.extract_data_from_cassandra,
)
```

### 6.4 Transform
<img src=assets/transform.png weight="500px" height="250px">

<b> Airflow tasks </b>

```python
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
```

### 6.5 Load data to Redshift
<img src=assets/load.png weight="500px" height="250px">

<b> Airflow tasks </b>

```python
Load = PythonOperator(
    task_id='Load_data_to_s3',
    python_callable=main_process.write_data_to_s3,
    op_args=[Transform.output]
)
```

## 7. Visualize result

Connect redshift to grafana and visualize results

<div style="display: flex; flex-direction: column;">
  <img src=assets/grafana_config.png alt="connect_grafana_redshift">
  <p> <b> <i> Connect to grafana </i> </b> </p>
</div>

### Visualization

<img src=assets/data_visualization.png>