import boto3

comprehend = boto3.client('comprehend')

def summarize_text(text):
    response = comprehend.detect_key_phrases(Text=text, LanguageCode='en')
    return ' '.join({p['Text'] for p in response['KeyPhrases']})