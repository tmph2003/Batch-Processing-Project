import psycopg2

def create_redshift_schema():
    redshift_host = 'redshift-cluster-1.cvzjnn720rwg.ap-southeast-1.redshift.amazonaws.com'
    redshift_port = '5439'
    redshift_dbname = 'dev'
    redshift_user = 'admin'
    redshift_password = '**********'

    aws_access_key_id = '**********'
    aws_secret_access_key = '**********'

    s3_bucket = 'recruitment-project-tmph2003'
    s3_key = 'result.csv/part-00000-3968dad8-5719-4173-973b-d1bcb9072400-c000.csv'

    sql_command = """
    CREATE TABLE IF NOT EXISTS result (
        job_id VARCHAR(255),
        publisher_id VARCHAR(255),
        campaign_id VARCHAR(255),
        group_id VARCHAR(255),
        Date VARCHAR(255),
        Hour VARCHAR(255),
        spend_hour VARCHAR(255),
        clicks VARCHAR(255),
        bid_set VARCHAR(255),
        conversion VARCHAR(255),
        qualified VARCHAR(255),
        unqualified VARCHAR(255),
        sources VARCHAR(255),
        company_id VARCHAR(255)
    );
    """

    conn = psycopg2.connect(
        host=redshift_host,
        port=redshift_port,
        dbname=redshift_dbname,
        user=redshift_user,
        password=redshift_password
    )

    cursor = conn.cursor()

    cursor.execute(sql_command)

    copy_command = f"""
    COPY result
    FROM 's3://{s3_bucket}/{s3_key}'
    CREDENTIALS 'aws_access_key_id={aws_access_key_id};aws_secret_access_key={aws_secret_access_key}'
    CSV
    IGNOREHEADER 1;
    """

    cursor.execute(copy_command)

    conn.commit()

    cursor.close()
    conn.close()