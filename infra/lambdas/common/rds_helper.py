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
from .secrets_helper import SecretsHelper

logger = get_logger(service="rds_helper", level="debug")
rds_client = boto3.client("rds")


class RDSHelper:
    @staticmethod
    def get_rds_auth_token(rds_config):
        try:
            token = rds_client.generate_db_auth_token(
                DBHostname=rds_config["host"],
                Port=rds_config["port"],
                DBUsername=rds_config["username"],
                Region=rds_config.get("region", boto3.session.Session().region_name),
            )
            return token
        except Exception as e:
            logger.exception(e)
            raise_error(f"Failed to generate RDS auth token: {e}")

    @staticmethod
    def get_connection_with_secret(secret_name, database_name):
        try:
            secret = SecretsHelper.get_secret(secret_name)
            connection = psycopg2.connect(
                host=secret["host"],
                port=secret["port"],
                user=secret["username"],
                password=secret["password"],
                database=database_name,
                sslmode="require",
            )
            return connection
        except Exception as e:
            logger.exception(e)
            raise_error(
                f"Database error: Failed to get_connection using Secrets Manager: {e}"
            )

    @staticmethod
    def get_connection_with_iam(rds_config):
        try:
            token = RDSHelper.get_rds_auth_token(rds_config)
            connection = psycopg2.connect(
                host=rds_config["host"],
                port=rds_config["port"],
                user=rds_config["username"],
                password=token,
                database=rds_config["database"],
                sslmode="require",
            )
            return connection
        except Exception as e:
            logger.exception(e)
            raise_error(
                f"Database error: Failed to get_connection using IAM authentication: {e}"
            )

    @staticmethod
    def execute_query(connection, query):
        try:
            with connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                cursor.execute(query)
                connection.commit()
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
