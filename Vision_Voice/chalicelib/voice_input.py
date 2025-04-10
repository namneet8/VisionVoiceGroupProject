import speech_recognition as sr

def get_voice_response():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source, timeout=5)
    return recognizer.recognize_google(audio).lower()