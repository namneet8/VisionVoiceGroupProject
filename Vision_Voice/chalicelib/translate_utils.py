import boto3

translate = boto3.client('translate')

def translate_text(text, target_language_code='fr'):
    if not text.strip():
        return text
        
    response = translate.translate_text(
        Text=text,
        SourceLanguageCode='auto',
        TargetLanguageCode=target_language_code
    )
    return response['TranslatedText']