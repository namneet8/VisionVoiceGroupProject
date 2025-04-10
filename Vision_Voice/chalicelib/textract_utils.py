import boto3

textract = boto3.client('textract')

def extract_text_from_image(s3_filename):
    response = textract.analyze_document(
        Document={'S3Object': {'Bucket': 'visionvoicegroupproject', 'Name': s3_filename}},
        FeatureTypes=["FORMS"]
    )
    return ' '.join(block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE')