import os
import tempfile
import boto3
from .s3_utils import upload_to_s3, generate_presigned_url

s3 = boto3.client('s3')
polly = boto3.client('polly')
bucket_name = 'visionvoicegroupproject'  # Should match your bucket name

def text_to_speech(text, s3_filename='speech.mp3'):
    if not text.strip():
        raise ValueError("Empty text cannot be converted to speech")
    
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Joanna'
    )
    
    if "AudioStream" in response:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(response['AudioStream'].read())
            f.flush()
            s3.upload_file(f.name, bucket_name, s3_filename)
        os.remove(f.name)
        
        return generate_presigned_url(s3_filename)
    return None