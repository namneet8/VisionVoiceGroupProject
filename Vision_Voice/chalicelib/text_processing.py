from textblob import TextBlob

def correct_spelling(text):
    blob = TextBlob(text)
    return str(blob.correct())