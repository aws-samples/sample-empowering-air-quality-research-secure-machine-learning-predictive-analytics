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
DB_NAME = get_env("DB_NAME")
INITIAL_DATA_FILE = get_env("INITIAL_DATA_FILE", "init_data.csv")

logger = get_logger(service=SERVICE_NAME, level=LOG_LEVEL)

# Log all environment variables at startup for debugging
logger.info(f"Environment variables: DB_TABLE={DB_TABLE}, DB_NAME={DB_NAME}, "
            f"READER_ROLE_NAME={READER_ROLE_NAME}, WRITER_ROLE_NAME={WRITER_ROLE_NAME}, "
            f"SOURCE_BUCKET={SOURCE_BUCKET}, INITIAL_DATA_PREFIX={INITIAL_DATA_PREFIX}, "
            f"INITIAL_DATA_FILE={INITIAL_DATA_FILE}")

def get_csv_from_s3(bucket, key):
    try:
        logger.info(f"Attempting to read CSV from S3: {bucket}/{key}")
        csv_data = S3Helper.read_from_s3(bucket, key)
        csv_file = io.StringIO(csv_data)
        reader = csv.DictReader(csv_file)
        columns = reader.fieldnames
        data = list(reader)
        logger.info(f"Successfully read CSV with {len(data)} rows and columns: {columns}")
        return columns, data
    except Exception as e:
        logger.error(f"Error reading CSV file from S3: {str(e)}")
        raise

def check_database_exists(conn, dbname):
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        exists = cur.fetchone() is not None
        logger.info(f"Database '{dbname}' exists: {exists}")
        return exists

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
        exists = cur.fetchone()[0]
        logger.info(f"Table '{table_name}' exists: {exists}")
        return exists

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
            logger.info(f"Table '{table_name}' already exists according to SQLAlchemy inspector")
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
        logger.info(f"Creating table: {table_name} with columns: {[c.name for c in table_columns]}")
        metadata.create_all(engine, tables=[table])
        
        # Verify table was created
        with conn.cursor() as cur:
            cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)", (table_name,))
            table_created = cur.fetchone()[0]
            logger.info(f"Table '{table_name}' creation verification: {table_created}")
            
            if table_created:
                # Get column information
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns_info = cur.fetchall()
                logger.info(f"Table '{table_name}' columns: {columns_info}")
        
        logger.info(f"Table '{table_name}' created successfully")
        return True
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
            logger.info(f"Insert SQL: {insert_sql} (showing query structure only, not values)")
            
            # Prepare batch of records with proper type conversion
            batch_records = []
            for row in data:
                record = []
                for col in columns:
                    # Handle empty strings for numeric columns
                    if col.lower() == 'value' and (row[col] == '' or row[col] is None):
                        record.append(None)  # Use NULL instead of empty string
                    elif any(num in col.lower() for num in ["amount", "price", "value", "pm25", "pm10"]) and (row[col] == '' or row[col] is None):
                        record.append(None)  # Use NULL for any numeric column with empty value
                    else:
                        record.append(row[col])
                        
                record.append(False)  # Add predicted_label value as False
                batch_records.append(tuple(record))
            
            # Execute many for better performance with the safe SQL
            cur.executemany(insert_sql, batch_records)
            conn.commit()
            logger.info(
                f"Successfully inserted {len(batch_records)} records into {table_name}"
            )
            
            # Verify data was inserted
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            count = cur.fetchone()[0]
            logger.info(f"Total records in {table_name} after insert: {count}")
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
            else:
                logger.info("Reader user already exists")

            # Create and configure writer_user
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname='writer_user'")
            if not cur.fetchone():
                cur.execute("CREATE USER writer_user")
                logger.info("Writer user created successfully")
            else:
                logger.info("Writer user already exists")

            # Grant basic permissions to database
            cur.execute(
                """
                GRANT rds_iam TO reader_user;
                GRANT CONNECT ON DATABASE %s TO reader_user;
                GRANT USAGE ON SCHEMA public TO reader_user;
                """,
                (psycopg2.extensions.AsIs(DB_NAME),)
            )
            
            cur.execute(
                """
                GRANT rds_iam TO writer_user;
                GRANT CONNECT ON DATABASE %s TO writer_user;
                GRANT USAGE ON SCHEMA public TO writer_user;
                """,
                (psycopg2.extensions.AsIs(DB_NAME),)
            )
            logger.info("Granted basic database permissions to users")

            # Grant permissions on existing tables and sequences
            cur.execute(
                """
                GRANT SELECT ON ALL TABLES IN SCHEMA public TO reader_user;
                GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO reader_user;
                """
            )
            
            cur.execute(
                """
                GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO writer_user;
                GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO writer_user;
                """
            )
            logger.info("Granted permissions on existing tables and sequences")

            # Set default privileges for future objects
            cur.execute(
                """
                ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                GRANT SELECT ON TABLES TO reader_user;
                
                ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                GRANT SELECT ON SEQUENCES TO reader_user;
                """
            )
            
            cur.execute(
                """
                ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO writer_user;
                
                ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                GRANT USAGE ON SEQUENCES TO writer_user;
                """
            )
            logger.info("Set default privileges for future objects")

            # Associate IAM roles with DB users
            for role_name, base_user in [
                (reader_role_name, "reader_user"),
                (writer_role_name, "writer_user"),
            ]:
                # Check if role exists
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
                    logger.info(f"Created IAM role {role_name}")
                else:
                    logger.info(f"IAM role {role_name} already exists")
                
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
                logger.info(f"IAM role {role_name} associated with {base_user}")
            
            # Explicitly grant permissions on the specific table if it exists
            # This is important to ensure the roles have access to the table
            if check_table_exists(conn, DB_TABLE):
                # Grant to base users
                cur.execute(
                    'GRANT SELECT ON TABLE public."%s" TO reader_user, writer_user',
                    (psycopg2.extensions.AsIs(DB_TABLE),)
                )
                cur.execute(
                    'GRANT INSERT, UPDATE, DELETE ON TABLE public."%s" TO writer_user',
                    (psycopg2.extensions.AsIs(DB_TABLE),)
                )
                
                # Grant to IAM roles directly
                cur.execute(
                    'GRANT SELECT ON TABLE public."%s" TO "%s", "%s"',
                    (
                        psycopg2.extensions.AsIs(DB_TABLE),
                        psycopg2.extensions.AsIs(reader_role_name),
                        psycopg2.extensions.AsIs(writer_role_name)
                    )
                )
                cur.execute(
                    'GRANT INSERT, UPDATE, DELETE ON TABLE public."%s" TO "%s"',
                    (
                        psycopg2.extensions.AsIs(DB_TABLE),
                        psycopg2.extensions.AsIs(writer_role_name)
                    )
                )
                logger.info(f"Explicitly granted permissions on table {DB_TABLE}")
            else:
                logger.warning(f"Table {DB_TABLE} does not exist yet, skipping explicit grants")
            
            # Verify permissions were granted correctly
            cur.execute(
                """
                SELECT grantee, table_name, privilege_type
                FROM information_schema.table_privileges
                WHERE table_name = %s
                ORDER BY grantee, privilege_type
                """,
                (DB_TABLE,)
            )
            permissions = cur.fetchall()
            logger.info(f"Current permissions on {DB_TABLE}: {permissions}")

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

            # List all tables in the database for debugging
            with conn.cursor() as cur:
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = cur.fetchall()
                logger.info(f"Tables in database before initialization: {tables}")

            # First get the data and create the table
            columns, csv_data = get_csv_from_s3(SOURCE_BUCKET, s3_key)

            if not check_table_exists(conn, DB_TABLE):
                table_created = create_table_dynamically(conn, DB_TABLE, columns)
                if not table_created:
                    logger.error(f"Failed to create table {DB_TABLE}")
                    # Try a direct SQL approach as fallback
                    with conn.cursor() as cur:
                        # Create a simple table with value and predicted_label columns
                        cur.execute(f"""
                            CREATE TABLE IF NOT EXISTS "{DB_TABLE}" (
                                id SERIAL PRIMARY KEY,
                                value INTEGER,
                                predicted_label BOOLEAN DEFAULT FALSE
                            )
                        """)
                        logger.info(f"Attempted fallback table creation for {DB_TABLE}")
            else:
                logger.info(f"Table '{DB_TABLE}' already exists")

            # Insert data
            insert_data_dynamically(conn, DB_TABLE, columns, csv_data)
            
            # Now create users and grant permissions AFTER the table exists
            create_db_users(conn, READER_ROLE_NAME, WRITER_ROLE_NAME)

            # Final verification
            with conn.cursor() as cur:
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = cur.fetchall()
                logger.info(f"Tables in database after initialization: {tables}")
                
                # Check specifically for our table
                cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s)", (DB_TABLE,))
                table_exists = cur.fetchone()[0]
                logger.info(f"Final verification - Table {DB_TABLE} exists: {table_exists}")
                
                if table_exists:
                    # Check permissions
                    cur.execute("""
                        SELECT grantee, privilege_type
                        FROM information_schema.table_privileges
                        WHERE table_name = %s
                    """, (DB_TABLE,))
                    permissions = cur.fetchall()
                    logger.info(f"Final verification - Permissions on {DB_TABLE}: {permissions}")

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
