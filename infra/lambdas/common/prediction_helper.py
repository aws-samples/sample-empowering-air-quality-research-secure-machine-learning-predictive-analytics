###
# © 2025 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
# This AWS Content is provided subject to the terms of the AWS Customer Agreement
# available at http://aws.amazon.com/agreement or other written agreement between
# Customer and either Amazon Web Services, Inc. or Amazon Web Services EMEA SARL or both.
###

from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List
import csv
from io import StringIO
from .logging import get_logger
from .s3_helper import S3Helper

logger = get_logger(service="predictions_helper", level="debug")


class PredictionsHelper:
    def round_to_two_decimals(value: float) -> float:
        """Helper function to round numbers to 2 decimal places"""
        try:
            # Using Decimal for more precise rounding
            return float(
                Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
        except:
            return value

    @staticmethod
    def parse_predictions_from_s3(
        bucket: str, file_key: str, region: str = "us-east-1"
    ) -> List[Dict]:
        try:
            # Read file from S3
            file_content = S3Helper.read_from_s3(bucket, file_key, region)
            if file_content is None:
                logger.error("Failed to read file from S3")
                return None
            logger.debug(f"File content: {file_content}")
            # Create a CSV reader from string
            csv_file = StringIO(file_content)
            csv_reader = csv.DictReader(csv_file)

            # Extract id and predicted values
            predictions = []
            for row in csv_reader:
                try:
                    if "id" not in row or "predicted_value" not in row:
                        logger.error(
                            "Required columns (id or predicted_value) not found in CSV"
                        )
                        continue

                    raw_value = float(row["predicted_value"])
                    rounded_predicted_value = PredictionsHelper.round_to_two_decimals(
                        raw_value
                    )

                    prediction_entry = {
                        "id": row["id"],
                        "predicted_value": rounded_predicted_value,
                    }
                    predictions.append(prediction_entry)

                except ValueError as ve:
                    logger.error(f"Invalid value in row {row}: {str(ve)}")
                    continue

            return predictions

        except Exception as e:
            logger.error(f"Error parsing predictions: {str(e)}")
            return None

    # Utility function to validate prediction data
    def validate_prediction(pred: Dict) -> bool:
        try:
            if not pred.get("id"):
                return False

            # Validate id format if needed
            # Add your id validation logic here

            # Validate predicted value
            pred_value = float(pred.get("predicted_value", 0))
            if pred_value < 0:  # Add your validation rules
                return False

            return True

        except ValueError:
            return False

    # Alternative version using column indices if CSV structure is fixed
    def parse_predictions_by_index(
        file_content: str, id_column: int = 0, pred_column: int = 1
    ) -> List[Dict]:
        try:
            predictions = []
            csv_file = StringIO(file_content)
            csv_reader = csv.reader(csv_file)

            # Skip header
            next(csv_reader)

            for row in csv_reader:
                try:
                    if len(row) <= max(id_column, pred_column):
                        logger.error(f"Row does not contain enough columns: {row}")
                        continue

                    # Round the predicted_value to 2 decimal places
                    raw_value = float(row["predicted_value"])
                    rounded_predicted_value = round_to_two_decimals(raw_value)

                    prediction_entry = {
                        "id": row[id_column],
                        "predicted_value": rounded_predicted_value,
                    }
                    predictions.append(prediction_entry)

                except ValueError as ve:
                    logger.error(f"Invalid numeric value in row {row}: {str(ve)}")
                    continue

            return predictions

        except Exception as e:
            logger.error(f"Error parsing predictions: {str(e)}")
            return None
