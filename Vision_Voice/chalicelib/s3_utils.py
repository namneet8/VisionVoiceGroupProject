import boto3
import os
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
bucket_name = os.getenv('S3_BUCKET', 'visionvoicegroupproject')

def upload_to_s3(file_path, s3_filename):
    """Upload a file to S3 bucket with explicit credentials"""
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        
        bucket_name = os.getenv("S3_BUCKET_NAME")
        
        with open(file_path, 'rb') as f:
            s3.upload_fileobj(f, bucket_name, s3_filename)
            
        return True
    except ClientError as e:
        print(f"S3 Upload Error: {e}")
        raise
    except Exception as e:
        print(f"General Upload Error: {e}")
        raise

def generate_presigned_url(s3_filename, expiration=3600):
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': s3_filename},
        ExpiresIn=expiration
    )