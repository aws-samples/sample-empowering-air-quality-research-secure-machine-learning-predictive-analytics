###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

import psycopg2
import boto3
import psycopg2.extras

from .logging import get_logger
from .error_helper import raise_error

logger = get_logger(service="rds_helper", level="debug")
client = boto3.client("rds")


class RDSHelper:
    def get_rds_auth_token(rds_config):
        password = client.generate_db_auth_token(
            DBHostname=rds_config["host"],
            Port=rds_config["port"],
            DBUsername=rds_config["username"],
        )
        return password

    @staticmethod
    def get_connection(rds_config):
        try:
            with psycopg2.connect(
                host=rds_config["host"],
                user=rds_config["username"],
                password=RDSHelper.get_rds_auth_token(rds_config),
                database=rds_config["database"],
            ) as connection:
                return connection
        except Exception as e:
            logger.exception(e)
            raise_error(f"Database error: Failed to get_connection from token: {e}")

    @staticmethod
    def get_connection_with_password(rds_config):
        try:
            with psycopg2.connect(
                host=rds_config["host"],
                user=rds_config["username"],
                password=rds_config["password"],
                database=rds_config["database"],
            ) as connection:
                return connection
        except Exception as e:
            logger.exception(e)
            raise_error(f"Database error: Failed to get_connection from password: {e}")

    @staticmethod
    def execute_query(connection, query):
        try:
            with connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                cursor.execute(query)
        except Exception as e:
            logger.exception(e)
            raise_error(f"Database error: Failed to execute_query: {e}")
        finally:
            logger.debug("Closing connection")
            connection.close()

    @staticmethod
    def execute_query_with_params(connection, query, params=None):
        try:
            with connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                cursor.execute(query, params)
                connection.commit()
        except Exception as e:
            logger.exception(e)
            raise_error(f"Database error: Failed to execute_query: {e}")
        finally:
            logger.debug("Closing connection")
            connection.close()

    @staticmethod
    def execute_update_query_with_params_and_result(connection, query, params=None):
        try:
            with connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                cursor.execute(query, params)
                # result = cursor.fetchone()
                connection.commit()
            return 1
        except Exception as e:
            logger.exception(e)
            raise_error(
                f"Database error: Failed to execute_update_query_with_params_and_result: {e}"
            )
        finally:
            logger.debug("Closing connection")
            connection.close()

    @staticmethod
    def execute_query_with_result_and_close(connection, query, params=None):
        try:
            with connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                if params is None:
                    cursor.execute(query)
                else:
                    cursor.execute(query, params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            logger.exception(e)
            raise_error(
                f"Database error: Failed to execute_query_with_result_and_close: {e}"
            )
        finally:
            logger.debug("Closing connection")
            connection.close()
