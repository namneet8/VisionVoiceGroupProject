import streamlit as st
import tempfile
import os
from chalicelib import (
    s3_utils,
    textract_utils,
    comprehend_utils,
    polly_utils,
    translate_utils
)

def main():
    st.title("✍️ VisionVoice: Handwriting to Voice")
    
    uploaded_file = st.file_uploader("Upload a handwritten image", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        # Process file and get extracted text
        extracted_text, s3_filename = process_file(uploaded_file)
        
        if extracted_text:  # Only proceed if text extraction succeeded
            display_interface(extracted_text, s3_filename)

def process_file(uploaded_file):
    """Handle file processing and return extracted text with filename"""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = tmp_file.name
        s3_filename = uploaded_file.name
        
        try:
            # Upload to S3
            s3_utils.upload_to_s3(tmp_path, s3_filename)
            
            # Extract text
            extracted_text = textract_utils.extract_text_from_image(s3_filename)
            return extracted_text, s3_filename
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            return None, None
        finally:
            os.unlink(tmp_path)

def display_interface(extracted_text, s3_filename):
    """Handle all UI components after text extraction"""
    st.subheader("📝 Extracted Text")
    st.write(extracted_text)
    
    # Handle summary workflow
    final_text = handle_summary_choice(extracted_text)
    
    # Handle translation workflow
    final_text = handle_translation(final_text)
    
    # Handle speech conversion
    handle_speech_conversion(final_text)

def handle_summary_choice(extracted_text):
    """Manage summary selection workflow"""
    if len(extracted_text) > 100:
        st.subheader("💬 The text is long. Would you like a summary?")
        col1, col2 = st.columns(2)
        
        if col1.button("Yes, summarize"):
            with st.spinner("Summarizing text..."):
                return comprehend_utils.summarize_text(extracted_text)
        if col2.button("No, use full text"):
            return extracted_text
            
    return extracted_text

def handle_translation(text):
    """Manage translation workflow"""
    st.subheader("🌍 Translation Options")
    target_lang = st.selectbox(
        "Choose a language for translation",
        ["None", "Spanish", "French", "German", "Chinese"]
    )
    
    lang_code_map = {
        "Spanish": "es",
        "French": "fr",
        "German": "de",
        "Chinese": "zh"
    }
    
    if target_lang != "None":
        with st.spinner(f"Translating to {target_lang}..."):
            translated_text = translate_utils.translate_text(
                text, 
                lang_code_map[target_lang]
            )
            st.subheader("🌐 Translated Text")
            st.write(translated_text)
            return translated_text
            
    return text

def handle_speech_conversion(text):
    """Manage text-to-speech conversion"""
    if st.button("🔊 Convert to Speech"):
        with st.spinner("Generating audio..."):
            try:
                clean_text = ''.join(c for c in text if c.isprintable())
                audio_url = polly_utils.text_to_speech(clean_text)
                
                if audio_url:
                    st.audio(audio_url, format="audio/mp3")
                    st.success("✅ Audio generated successfully!")
                    st.markdown(f"[Download Audio]({audio_url})")
                else:
                    st.error("Failed to generate audio")
            except Exception as e:
                st.error(f"Error generating speech: {str(e)}")

if __name__ == "__main__":
    main()