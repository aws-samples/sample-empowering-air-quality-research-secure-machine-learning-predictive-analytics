import os
import csv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from common import SecretsHelper, S3Helper, get_env, get_logger

SECRET_NAME = get_env("SECRET_NAME")
REGION = get_env("AWS_REGION", "us-east-1")
DB_TABLE = get_env("DB_TABLE")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "db_init_lambda")
DB_DUMP_PREFIX = get_env("DB_DUMP_PREFIX", "initial_db_dump_files")
DB_DUMP_FILE_KEY = get_env("DB_DUMP_FILE", "init_data.csv")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
PROCESS_LOCAL = get_env("PROCESS_LOCAL", "true")
logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


def get_csv_columns_and_data(csv_path):
    try:
        lambda_path = os.path.join(os.path.dirname(__file__), csv_path)
        with open(lambda_path, "r") as file:
            reader = csv.DictReader(file)
            # Get column names from CSV
            columns = reader.fieldnames
            # Read all data
            data = list(reader)
            return columns, data
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        raise


def get_csv_from_s3(bucket, csv_path):
    try:
        csv_data = S3Helper.read_from_s3(bucket, csv_path)
        columns = csv_data.split("\n")[0].split(",")
        data = csv_data.split("\n")[1:]
        return columns, data
    except Exception as e:
        logger.error(f"Error reading CSV file from S3: {str(e)}")
        raise


def create_table_dynamically(conn, table_name, columns):
    try:
        with conn.cursor() as cur:
            # Start with basic SQL for table creation
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
            """

            # Add columns based on CSV headers
            column_definitions = []
            for col in columns:
                # You can add more data type mappings based on your needs
                if col.lower().endswith("_at") or col.lower() == "timestamp":
                    col_type = "TIMESTAMP WITH TIME ZONE"
                elif col.lower().startswith("is_") or col.lower().startswith("has_"):
                    col_type = "BOOLEAN"
                elif any(
                    num in col.lower()
                    for num in ["amount", "price", "value", "pm25", "pm10"]
                ):
                    col_type = "FLOAT"
                else:
                    col_type = "VARCHAR(255)"

                column_definitions.append(f"{col} {col_type}")

            # Add predicted_label if not in columns
            if "predicted_label" not in [col.lower() for col in columns]:
                column_definitions.append("predicted_label BOOLEAN DEFAULT FALSE")

            # Complete the CREATE TABLE statement
            create_table_sql += ",\n".join(column_definitions)
            create_table_sql += "\n)"

            logger.info(f"Executing SQL: {create_table_sql}")

            # Execute the CREATE TABLE statement
            cur.execute(create_table_sql)
            logger.info(
                f"Table '{table_name}' created/verified successfully with columns: {columns}"
            )
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        raise


def insert_data_dynamically(conn, table_name, columns, data):
    try:
        with conn.cursor() as cur:
            # Add predicted_label to columns if not present
            all_columns = list(columns)
            if "predicted_label" not in [col.lower() for col in all_columns]:
                all_columns.append("predicted_label")

            # Create the INSERT statement dynamically
            columns_str = ", ".join(all_columns)
            placeholders = ", ".join(["%s"] * len(all_columns))
            insert_sql = f"""
                INSERT INTO {table_name} ({columns_str})
                VALUES ({placeholders})
            """

            # Prepare batch of records
            records = []
            for row in data:
                # Extract values in the same order as columns and add predicted_label
                record = [row[col] for col in columns]
                record.append(False)  # Add predicted_label value as False for CSV data
                records.append(record)

            # Execute batch insert
            cur.executemany(insert_sql, records)
            conn.commit()
            logger.info(
                f"Successfully inserted {len(records)} records into {table_name}"
            )
    except Exception as e:
        logger.error(f"Error inserting data: {str(e)}")
        conn.rollback()
        raise


def lambda_handler(event, context):
    try:
        # Get database credentials from Secrets Manager
        secret = SecretsHelper.get_secret(SECRET_NAME)
        if not secret:
            raise RuntimeError(
                "Failed to retrieve database credentials from Secrets Manager"
            )

        # Get database connection parameters
        host = get_env("DB_HOST")
        port = int(get_env("RDS_DB_PORT", "5432"))
        dbname = get_env("DB_NAME", "aqdb")
        user = secret["username"]
        password = secret["password"]

        # First connect to default postgres database
        conn = None
        try:
            conn = psycopg2.connect(
                host=host, port=port, dbname="postgres", user=user, password=password
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            # Create database if it doesn't exist
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
                if not cur.fetchone():
                    cur.execute("CREATE DATABASE %s", (dbname,))
                    logger.info(f"Database '{dbname}' created successfully")
        finally:
            if conn:
                conn.close()

        # Connect to the new database
        conn = None
        try:
            conn = psycopg2.connect(
                host=host, port=port, dbname=dbname, user=user, password=password
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

            # Read CSV columns and data
            read_local = PROCESS_LOCAL.lower() == "true"
            columns, csv_data = (
                get_csv_columns_and_data(DB_DUMP_FILE_KEY)
                if read_local
                else get_csv_from_s3(
                    SOURCE_BUCKET, DB_DUMP_PREFIX + "/" + DB_DUMP_FILE_KEY
                )
            )

            # Create table with dynamic columns
            create_table_dynamically(conn, DB_TABLE, columns)

            # Insert data into table
            insert_data_dynamically(conn, DB_TABLE, columns, csv_data)

            return {
                "statusCode": 200,
                "body": "Database initialization completed successfully",
            }

        except Exception as e:
            logger.error(f"Error during database operations: {str(e)}")
            raise

        finally:
            if conn:
                conn.close()

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        return {"statusCode": 500, "body": f"Database initialization failed: {str(e)}"}
