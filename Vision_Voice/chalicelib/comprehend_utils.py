import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Comprehend client
comprehend = boto3.client('comprehend')

def summarize_text(text):
    """Summarize input text using AWS Comprehend's key phrase detection, with logging and error handling."""
    try:
        logger.info("Audit: Starting key phrase extraction with AWS Comprehend")

        response = comprehend.detect_key_phrases(Text=text, LanguageCode='en')
        key_phrases = {p['Text'] for p in response.get('KeyPhrases', [])}
        summary = ' '.join(key_phrases)

        logger.info(f"Audit: Key phrase extraction successful - Found {len(key_phrases)} key phrases")
        return summary

    except (ClientError, BotoCoreError) as e:
        logger.error(f"Comprehend Client Error - Error: {e}", exc_info=True)
        raise RuntimeError("Failed to analyze text with AWS Comprehend") from e
    except Exception as e:
        logger.error(f"Unexpected error during key phrase extraction - Error: {e}", exc_info=True)
        raise RuntimeError("Unexpected error in text summarization") from e
