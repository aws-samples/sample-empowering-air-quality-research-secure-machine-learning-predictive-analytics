import csv
import io
import psycopg2
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Boolean, DateTime, inspect
from common import S3Helper, get_env, get_logger, RDSHelper

# Environment variables
DB_SECRET_NAME = get_env("DB_SECRET_NAME")
DB_TABLE = get_env("DB_TABLE")
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
SERVICE_NAME = get_env("SERVICE_NAME", "db_init_lambda")
INITIAL_DATA_PREFIX = get_env("INITIAL_DATA_PREFIX", "initial_dataset")
SOURCE_BUCKET = get_env("SOURCE_BUCKET")
READER_ROLE_NAME = get_env("READER_ROLE_NAME")
WRITER_ROLE_NAME = get_env("WRITER_ROLE_NAME")
DB_NAME = get_env("DB_NAME", "demodb")
INITIAL_DATA_FILE = get_env("INITIAL_DATA_FILE", "init_data.csv")

logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)


def get_csv_from_s3(bucket, key):
    try:
        csv_data = S3Helper.read_from_s3(bucket, key)
        csv_file = io.StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        columns = reader.fieldnames
        data = list(reader)
        return columns, data
    except Exception as e:
        logger.error(f"Error reading CSV file from S3: {str(e)}")
        raise


def check_database_exists(conn, dbname):
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        return cur.fetchone() is not None


def check_table_exists(conn, table_name):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            )
        """,
            (table_name,),
        )
        return cur.fetchone()[0]


def create_database(conn, dbname):
    with conn.cursor() as cur:
        cur.execute("CREATE DATABASE %s", (psycopg2.extensions.AsIs(dbname),))
        logger.info(f"Database '{dbname}' created successfully")


def create_table_dynamically(conn, table_name, columns):
    try:
        # Create SQLAlchemy engine from the psycopg2 connection
        engine = create_engine('postgresql://', creator=lambda: conn)
        metadata = MetaData()
        
        # Check if table already exists
        inspector = inspect(engine)
        if table_name in inspector.get_table_names():
            logger.info(f"Table '{table_name}' already exists")
            return
        
        # Define table columns programmatically
        table_columns = [Column('id', Integer, primary_key=True)]
        
        for col in columns:
            # Determine column type based on naming conventions
            if col.lower().endswith("_at") or col.lower() == "timestamp":
                col_type = DateTime
            elif col.lower().startswith("is_") or col.lower().startswith("has_"):
                col_type = Boolean
            elif any(
                num in col.lower()
                for num in ["amount", "price", "value", "pm25", "pm10"]
            ):
                col_type = Float
            else:
                col_type = String(255)
            
            # Add column to the list
            table_columns.append(Column(col, col_type))
        
        # Add predicted_label if not present
        if "predicted_label" not in [col.lower() for col in columns]:
            table_columns.append(Column("predicted_label", Boolean, default=False))
        
        # Create table definition
        table = Table(table_name, metadata, *table_columns)
        
        # Create the table in the database
        logger.info(f"Creating table: {table_name}")
        metadata.create_all(engine, tables=[table])
        
        logger.info(
            f"Table '{table_name}' created successfully with columns: {columns}"
        )
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        raise


def insert_data_dynamically(conn, table_name, columns, data):
    try:
        with conn.cursor() as cur:
            all_columns = list(columns)
            if "predicted_label" not in [col.lower() for col in all_columns]:
                all_columns.append("predicted_label")
            
            # Safely quote column names
            quoted_columns = [f'"{col}"' for col in all_columns]
            column_names = ", ".join(quoted_columns)
            
            # Create placeholders for values
            placeholders = ", ".join(["%s" for _ in range(len(all_columns))])
            
            # Prepare the table name safely using psycopg2's identifier quoting
            quoted_table = f'"{table_name}"'
            
            # Construct a safe parameterized query
            insert_sql = f"INSERT INTO {quoted_table} ({column_names}) VALUES ({placeholders})"
            
            # Prepare batch of records
            batch_records = []
            for row in data:
                record = [row[col] for col in columns]
                record.append(False)  # Add predicted_label value as False
                batch_records.append(tuple(record))
            
            # Execute many for better performance with the safe SQL
            cur.executemany(insert_sql, batch_records)
            conn.commit()
            logger.info(
                f"Successfully inserted {len(batch_records)} records into {table_name}"
            )
    except Exception as e:
        logger.error(f"Error inserting data: {str(e)}")
        conn.rollback()
        raise


def create_db_users(conn, reader_role_name, writer_role_name):
    try:
        with conn.cursor() as cur:
            # Create and configure reader_user
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname='reader_user'")
            if not cur.fetchone():
                cur.execute("CREATE USER reader_user")
                logger.info("Reader user created successfully")

            # Use parameterized queries for database name
            cur.execute(
                """
                GRANT rds_iam TO reader_user;
                GRANT CONNECT ON DATABASE %s TO reader_user;
                GRANT USAGE ON SCHEMA public TO reader_user;
                GRANT SELECT ON ALL TABLES IN SCHEMA public TO reader_user;
                GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO reader_user;
            """,
                (psycopg2.extensions.AsIs(f'"{DB_NAME}"'),)
            )

            # Create and configure writer_user
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname='writer_user'")
            if not cur.fetchone():
                cur.execute("CREATE USER writer_user")
                logger.info("Writer user created successfully")

            # Use parameterized queries for database name
            cur.execute(
                """
                GRANT rds_iam TO writer_user;
                GRANT CONNECT ON DATABASE %s TO writer_user;
                GRANT USAGE ON SCHEMA public TO writer_user;
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO writer_user;
                GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO writer_user;
            """,
                (psycopg2.extensions.AsIs(f'"{DB_NAME}"'),)
            )

            # Associate IAM roles with DB users
            for role_name, base_user in [
                (reader_role_name, "reader_user"),
                (writer_role_name, "writer_user"),
            ]:
                # Check if role exists using quoted identifier
                cur.execute(
                    "SELECT 1 FROM pg_roles WHERE rolname=%s", 
                    (role_name,)
                )
                if not cur.fetchone():
                    # Create the role with proper quoting
                    cur.execute(
                        'CREATE USER "%s" WITH LOGIN',
                        (psycopg2.extensions.AsIs(role_name),)
                    )
                    
                    # Grant permissions with proper quoting
                    cur.execute(
                        'GRANT rds_iam TO "%s"',
                        (psycopg2.extensions.AsIs(role_name),)
                    )
                    
                    cur.execute(
                        'GRANT %s TO "%s"',
                        (
                            psycopg2.extensions.AsIs(base_user),
                            psycopg2.extensions.AsIs(role_name),
                        )
                    )
                    
                    logger.info(
                        f"IAM role {role_name} associated with DB user successfully"
                    )
                    
            # Explicitly grant permissions on the specific table
            # This is important to ensure the roles have access to tables created after the roles
            cur.execute(
                "GRANT SELECT ON TABLE public.%s TO reader_user, writer_user",
                (psycopg2.extensions.AsIs(f'"{DB_TABLE}"'),)
            )
            cur.execute(
                "GRANT INSERT, UPDATE, DELETE ON TABLE public.%s TO writer_user",
                (psycopg2.extensions.AsIs(f'"{DB_TABLE}"'),)
            )
            
            # Also grant permissions to the IAM roles directly to ensure access
            cur.execute(
                "GRANT SELECT ON TABLE public.%s TO %s, %s",
                (
                    psycopg2.extensions.AsIs(f'"{DB_TABLE}"'),
                    psycopg2.extensions.AsIs(f'"{reader_role_name}"'),
                    psycopg2.extensions.AsIs(f'"{writer_role_name}"')
                )
            )
            cur.execute(
                "GRANT INSERT, UPDATE, DELETE ON TABLE public.%s TO %s",
                (
                    psycopg2.extensions.AsIs(f'"{DB_TABLE}"'),
                    psycopg2.extensions.AsIs(f'"{writer_role_name}"')
                )
            )
            
            logger.info(f"Explicitly granted permissions on table {DB_TABLE}")

    except Exception as e:
        logger.error(f"Error creating DB users: {str(e)}")
        raise


def lambda_handler(event, context):
    try:
        s3_key = f"{INITIAL_DATA_PREFIX}/{INITIAL_DATA_FILE}"

        logger.info(f"Using S3 bucket: {SOURCE_BUCKET}, key: {s3_key}")

        # First connect to default postgres database
        conn = None
        try:
            conn = RDSHelper.get_connection_with_secret(DB_SECRET_NAME, "postgres")
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

            if not check_database_exists(conn, DB_NAME):
                create_database(conn, DB_NAME)
            else:
                logger.info(f"Database '{DB_NAME}' already exists")
        finally:
            if conn:
                conn.close()

        # Connect to the target database
        conn = None
        try:
            conn = RDSHelper.get_connection_with_secret(DB_SECRET_NAME, DB_NAME)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

            create_db_users(conn, READER_ROLE_NAME, WRITER_ROLE_NAME)

            columns, csv_data = get_csv_from_s3(SOURCE_BUCKET, s3_key)

            if not check_table_exists(conn, DB_TABLE):
                create_table_dynamically(conn, DB_TABLE, columns)
            else:
                logger.info(f"Table '{DB_TABLE}' already exists")

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
