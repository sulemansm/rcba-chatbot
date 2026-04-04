"""
s3_service.py — Upload lead JSON to AWS S3
"""

import os
import json
import logging
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


def upload_lead_to_s3(lead_data: dict) -> tuple[bool, str]:
    """
    Uploads lead_data as a JSON file to S3.
    Returns (success: bool, message: str).

    File path format: leads/YYYY-MM-DD-HH-MM-SS.json
    """
    bucket = os.environ.get("S3_BUCKET", "")
    region = os.environ.get("AWS_REGION", "ap-south-1")

    if not bucket:
        msg = "S3_BUCKET environment variable is not set."
        logger.error(msg)
        return False, msg

    # Build S3 key from timestamp
    now = datetime.utcnow()
    key = now.strftime("leads/%Y-%m-%d-%H-%M-%S.json")

    try:
        s3 = boto3.client("s3", region_name=region)
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(lead_data, indent=2),
            ContentType="application/json",
        )
        logger.info("Lead uploaded to s3://%s/%s", bucket, key)
        return True, f"Saved to s3://{bucket}/{key}"

    except ClientError as e:
        msg = f"S3 ClientError: {e.response['Error']['Message']}"
        logger.error(msg)
        return False, msg
    except BotoCoreError as e:
        msg = f"S3 BotoCoreError: {str(e)}"
        logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"S3 unexpected error: {str(e)}"
        logger.error(msg)
        return False, msg
