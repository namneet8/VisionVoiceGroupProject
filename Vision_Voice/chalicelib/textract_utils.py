import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Textract client
textract = boto3.client('textract')

def extract_text_from_image(s3_filename):
    """Extract structured text from an image using Textract with improved formatting preservation."""
    bucket_name = 'visionvoicegroupproject'

    try:
        logger.info(f"Audit: Textract analysis started - Bucket: {bucket_name}, Key: {s3_filename}")

        response = textract.analyze_document(
            Document={'S3Object': {'Bucket': bucket_name, 'Name': s3_filename}},
            FeatureTypes=["FORMS", "TABLES"]
        )

        blocks = response.get('Blocks', [])
        lines_by_y = []

        # Only LINE blocks
        for block in blocks:
            if block['BlockType'] == 'LINE':
                text = block['Text'].strip()
                y_coord = block['Geometry']['BoundingBox']['Top']
                lines_by_y.append((y_coord, text))

        # Sort by vertical Y position
        lines_by_y.sort(key=lambda x: x[0])

        formatted_text = ""
        previous_y = 0
        for idx, (y, text) in enumerate(lines_by_y):
            # Add line break if vertical distance is large (new paragraph)
            if idx > 0 and abs(y - previous_y) > 0.01:
                formatted_text += "\n"

            # Add bullet-like formatting if line starts with dash or bullet
            if text.lstrip().startswith(('-', '*', '•')):
                formatted_text += f"• {text.lstrip('-•* ').strip()}\n"
            else:
                formatted_text += text + "\n"

            previous_y = y

        logger.info(f"Audit: Textract analysis successful - Extracted {len(lines_by_y)} lines")
        return formatted_text.strip()

    except (ClientError, BotoCoreError) as e:
        logger.error(f"Textract Client Error - S3 Key: {s3_filename}, Error: {e}", exc_info=True)
        raise RuntimeError("Failed to analyze document with Textract") from e
    except Exception as e:
        logger.error(f"Unexpected error during Textract analysis - S3 Key: {s3_filename}, Error: {e}", exc_info=True)
        raise RuntimeError("Unexpected error in Textract text extraction") from e
