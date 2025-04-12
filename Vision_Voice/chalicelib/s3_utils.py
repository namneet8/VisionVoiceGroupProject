import boto3
import os
import logging
from botocore.exceptions import ClientError

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Setup S3 client
s3 = boto3.client('s3')
bucket_name = os.getenv('S3_BUCKET', 'visionvoicegroupproject')

def upload_to_s3(file_path, s3_filename):
    """Upload a file to an S3 bucket with explicit credentials and logging"""
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

        bucket_name = os.getenv("S3_BUCKET_NAME", "visionvoicegroupproject")
        
        logger.info(f"Audit: Upload started - File: {file_path}, S3 Key: {s3_filename}, Bucket: {bucket_name}")

        with open(file_path, 'rb') as f:
            s3.upload_fileobj(f, bucket_name, s3_filename)

        logger.info(f"Audit: Upload successful - File: {file_path}, S3 Key: {s3_filename}")
        return True

    except ClientError as e:
        logger.error(f"S3 Upload Error - File: {file_path}, Error: {e}", exc_info=True)
        raise RuntimeError("Failed to upload file to S3") from e
    except Exception as e:
        logger.error(f"General Upload Error - File: {file_path}, Error: {e}", exc_info=True)
        raise RuntimeError("Unexpected error during S3 upload") from e

def generate_presigned_url(s3_filename, expiration=3600):
    """Generate a pre-signed URL for an S3 object"""
    try:
        logger.info(f"Audit: Generating pre-signed URL - S3 Key: {s3_filename}, Expiration: {expiration}s")
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_filename},
            ExpiresIn=expiration
        )
        logger.info("Audit: Pre-signed URL generated successfully")
        return url
    except ClientError as e:
        logger.error(f"Pre-signed URL Error - S3 Key: {s3_filename}, Error: {e}", exc_info=True)
        raise RuntimeError("Failed to generate pre-signed URL") from e
    except Exception as e:
        logger.error(f"Unexpected error generating pre-signed URL - S3 Key: {s3_filename}, Error: {e}", exc_info=True)
        raise RuntimeError("Unexpected error during URL generation") from e
