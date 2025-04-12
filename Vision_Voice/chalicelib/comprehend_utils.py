import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError
import re

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add a handler to display logs in console
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Create the Comprehend client
comprehend = boto3.client('comprehend')


import re

def summarize_text(text, max_lines=4):
    """
    Generate a concise summary by extracting key sentences
    based on AWS Comprehend key phrases.
    """
    try:
        logger.info("🔍 Extracting key phrases from text")
        response = comprehend.detect_key_phrases(Text=text, LanguageCode='en')
        key_phrases = {p['Text'].lower() for p in response.get('KeyPhrases', []) if len(p['Text']) > 2}

        # Split the text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentence_scores = []

        for sentence in sentences:
            score = sum(1 for phrase in key_phrases if phrase in sentence.lower())
            sentence_scores.append((score, sentence))

        # Sort by score and select top N sentences
        sentence_scores.sort(reverse=True)
        selected_sentences = [s for _, s in sentence_scores[:max_lines]]

        # Combine selected sentences and return a summary
        summary = ' '.join(selected_sentences).strip()

        logger.info(f"✅ Summary generated with {len(selected_sentences)} key sentences")
        return summary

    except (ClientError, BotoCoreError) as e:
        logger.error("❌ AWS Comprehend error", exc_info=True)
        raise RuntimeError("Failed to analyze text using Comprehend") from e
    except Exception as e:
        logger.error("❌ Unexpected error during summarization", exc_info=True)
        raise RuntimeError("Error while summarizing text") from e

