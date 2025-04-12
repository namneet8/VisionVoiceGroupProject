import os
import tempfile
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from .s3_utils import upload_to_s3, generate_presigned_url
import xml.sax.saxutils as xml_utils

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS clients
s3 = boto3.client('s3')
polly = boto3.client('polly')

# Bucket name
bucket_name = 'visionvoicegroupproject'  # Should match your bucket name

def format_text_for_ssml(text):
    """Wraps text in SSML with special formatting for bullet points and natural pauses."""
    import re

    # Normalize bullets
    bullet_lines = []
    lines = text.strip().splitlines()

    for line in lines:
        line = line.strip()
        if re.match(r'^[-•*]', line):  # Detect bullet line
            content = re.sub(r'^[-•*]\s*', '', line)
            content = xml_utils.escape(content)
            bullet_lines.append(f'<p><break time="500ms"/>Bullet point: {content}.</p>')
        elif line:
            sentence_parts = re.split(r'(?<=[.!?]) +', line)
            for part in sentence_parts:
                if part.strip():
                    bullet_lines.append(f"<s>{xml_utils.escape(part.strip())}</s>")

    ssml = "<speak>\n" + "\n".join(bullet_lines) + "\n</speak>"
    return ssml



def text_to_speech(text, s3_filename='speech.mp3'):
    """Convert input text to speech, upload to S3, and return a pre-signed URL."""
    if not text.strip():
        logger.warning("Attempted text-to-speech with empty input")
        raise ValueError("Empty text cannot be converted to speech")
    
    try:
        logger.info(f"Audit: Text-to-speech synthesis started - Filename: {s3_filename}")
        ssml_text = format_text_for_ssml(text)

        response = polly.synthesize_speech(
            Text=ssml_text,
            TextType='ssml',
            OutputFormat='mp3',
            VoiceId='Joanna'
        )

        if "AudioStream" in response:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                f.write(response['AudioStream'].read())
                f.flush()
                local_path = f.name

            upload_to_s3(local_path, s3_filename)
            os.remove(local_path)

            logger.info(f"Audit: Speech synthesis and S3 upload successful - Filename: {s3_filename}")
            return generate_presigned_url(s3_filename)
        else:
            logger.error("Polly did not return an AudioStream")
            raise RuntimeError("Polly did not return an audio stream")

    except (BotoCoreError, ClientError) as e:
        logger.error(f"Polly or S3 client error - Error: {e}", exc_info=True)
        raise RuntimeError("AWS Polly or S3 operation failed") from e
    except Exception as e:
        logger.error(f"Unexpected error in text_to_speech - Error: {e}", exc_info=True)
        raise RuntimeError("Unexpected error in text-to-speech conversion") from e
