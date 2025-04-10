import boto3
import os

s3 = boto3.client('s3')
bucket_name = os.getenv('S3_BUCKET', 'visionvoicegroupproject')

def upload_to_s3(file_path, s3_filename):
    with open(file_path, 'rb') as f:
        s3.upload_fileobj(f, bucket_name, s3_filename)
    return f"https://{bucket_name}.s3.amazonaws.com/{s3_filename}"

def generate_presigned_url(s3_filename, expiration=3600):
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': s3_filename},
        ExpiresIn=expiration
    )