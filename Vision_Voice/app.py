import streamlit as st
import tempfile
import os
from chalicelib import (
    s3_utils,
    textract_utils,
    comprehend_utils,
    polly_utils,
    translate_utils,
    text_processing,
    pdf_utils
)

def main():
    st.title("✍ VisionVoice: Handwriting to Voice")
    
    uploaded_file = st.file_uploader("Upload a handwritten image", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        process_file(uploaded_file)

def process_file(uploaded_file):
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name
        s3_filename = uploaded_file.name
        
        try:
            # Upload to S3
            s3_utils.upload_to_s3(tmp_path, s3_filename)
            
            # Extract text
            st.info("🧠 Extracting handwritten text...")
            extracted_text = textract_utils.extract_text_from_image(s3_filename)
            
            # Show raw text
            st.subheader("📝 Raw Extracted Text:")
            st.write(extracted_text)
            
            # Correct spelling
            st.info("🔍 Correcting spelling errors...")
            corrected_text = text_processing.correct_spelling(extracted_text)
            st.subheader("✅ Corrected Text:")
            st.write(corrected_text)
            
            # Handle summarization
            final_text = handle_summarization(corrected_text)
            
            # Handle translation
            final_text = handle_translation(final_text)
            
            # Handle speech conversion
            handle_speech_conversion(final_text)
            
            # Handle PDF download
            handle_pdf_download(final_text)
            
        finally:
            os.unlink(tmp_path)

def handle_summarization(text):
    if len(text) > 1000:
        st.subheader("💬 The text is long. Would you like a summary?")
        choice = st.radio("Summarize?", ["No", "Yes"])
        if choice == "Yes":
            st.info("Summarizing with AWS Comprehend...")
            return comprehend_utils.summarize_text(text)
    return text

def handle_translation(text):
    st.subheader("🌍 Do you want to translate the text?")
    target_lang = st.selectbox("Choose a language", ["None", "Spanish", "French", "German", "Chinese"])
    lang_code_map = {
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Chinese": "zh"
    }

    if target_lang != "None":
        st.info(f"Translating to {target_lang}...")
        translated_text = translate_utils.translate_text(text, lang_code_map[target_lang])
        st.subheader("🌐 Translated Text:")
        st.write(translated_text)
        return translated_text
    return text

def handle_speech_conversion(text):
    if st.button("🔊 Convert to Speech"):
        clean_text = ''.join(c for c in text if c.isprintable())
        audio_url = polly_utils.text_to_speech(clean_text)
        if audio_url:
            st.audio(audio_url, format="audio/mp3")
            st.success("✅ Here’s your audio!")
            st.markdown(f"[⬇ Download Audio File]({audio_url})")

def handle_pdf_download(text):
    if st.button("📄 Download Text as PDF"):
        pdf_path = pdf_utils.generate_pdf(text)
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="Download PDF",
                data=f,
                file_name="extracted_text.pdf",
                mime="application/pdf"
            )
        os.remove(pdf_path)

if __name__ == "__main__":
    main()