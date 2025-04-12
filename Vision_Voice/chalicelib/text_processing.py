import logging
import re
from textblob import TextBlob

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def clean_and_format_sentences(text):
    """Clean spacing without forcefully altering sentence structure."""
    try:
        logger.info("Audit: Cleaning and formatting text")
        text = re.sub(r'[ \t]+', ' ', text)  # Collapse multiple spaces
        text = re.sub(r'(?<=[.!?])(?=\S)', ' ', text)  # Ensure space after punctuation
        return text.strip()
    except Exception as e:
        logger.error(f"Error during sentence cleanup - Error: {e}", exc_info=True)
        raise RuntimeError("Sentence cleanup failed") from e

