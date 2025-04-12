import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize AWS Translate client
translate = boto3.client('translate')

def translate_text(text, target_language_code='fr'):
    """Translate the given text to the target language using AWS Translate."""
    if not text.strip():
        logger.warning("Empty input text provided to translate_text")
        return text

    try:
        logger.info(f"Audit: Starting translation - Target language: {target_language_code}")

        response = translate.translate_text(
            Text=text,
            SourceLanguageCode='auto',
            TargetLanguageCode=target_language_code
        )

        translated_text = response.get('TranslatedText', '')
        logger.info("Audit: Translation successful")
        return translated_text

    except (BotoCoreError, ClientError) as e:
        logger.error(f"Translate client error - Error: {e}", exc_info=True)
        raise RuntimeError("Translation failed due to AWS error") from e
    except Exception as e:
        logger.error(f"Unexpected error in translate_text - Error: {e}", exc_info=True)
        raise RuntimeError("Unexpected error during translation") from e
