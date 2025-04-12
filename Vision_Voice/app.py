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
from datetime import datetime, timedelta
from urllib.parse import parse_qs
from dotenv import load_dotenv
import sys
import traceback
from chalicelib.subscription import (
    fetch_subscription_tier,
    display_pricing,
    check_upload_limit,
    increment_upload_count,
    has_feature
)
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

# Set up development mode
DEV_MODE = os.getenv('COGNITO_DEVELOPMENT_MODE', '').lower() in ('true', '1', 't')

# Try to import and initialize Cognito auth
try:
    from chalicelib.cognito_auth import CognitoAuth
    auth = CognitoAuth()
    auth_enabled = True
except Exception as e:
    if DEV_MODE:
        st.warning("⚠️ Running in development mode without authentication")
        auth_enabled = False
    else:
        st.error(f"❌ Authentication error: {str(e)}")
        st.error(traceback.format_exc())
        auth_enabled = False

def initialize_session_state():
    """Initialize session state variables"""
    defaults = {
        "authenticated": not auth_enabled or DEV_MODE,
        "user_info": {"name": "Developer", "email": "dev@example.com"} if DEV_MODE else None,
        "access_token": "dev-token" if DEV_MODE else None,
        "subscription_tier": "free" if DEV_MODE else None,
        "upload_count": 0,
        "last_reset": datetime.now().isoformat(),
        "manage_subscription": False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    # Add this to your initialization sequence to verify credentials
    print("AWS_ACCESS_KEY_ID exists:", os.getenv("AWS_ACCESS_KEY_ID") is not None)
    print("AWS_SECRET_ACCESS_KEY exists:", os.getenv("AWS_SECRET_ACCESS_KEY") is not None)
    print("AWS_REGION:", os.getenv("AWS_REGION"))
    print("S3_BUCKET_NAME:", os.getenv("S3_BUCKET_NAME"))

def handle_auth_callback():
    """Handle the OAuth callback after user login"""
    if not auth_enabled or DEV_MODE:
        return
    
    query_params = st.query_params
    if "code" in query_params:
        try:
            code = query_params["code"]
            
            # Prevent replay attacks
            if "last_processed_code" in st.session_state and st.session_state.last_processed_code == code:
                st.query_params.clear()
                return
            
            # Validate state
            if "state" in query_params and "oauth_state" in st.session_state:
                if query_params["state"] != st.session_state.oauth_state:
                    raise ValueError("State parameter mismatch")
            
            # Get tokens and user info
            tokens = auth.get_tokens(code)
            user_info = auth.get_user_info(tokens["access_token"])
            
            # Set session state
            st.session_state.update({
                "access_token": tokens["access_token"],
                "user_info": user_info,
                "authenticated": True,
                "last_processed_code": code,
                "oauth_state": None,
                "subscription_tier": fetch_subscription_tier(user_info["username"])
            })
            
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            st.session_state.authenticated = False
            st.query_params.clear()
            st.rerun()

def login_page():
    """Display login page"""
    st.title("✍ VisionVoice: Handwriting to Voice")
    st.header("Login")
    
    if auth_enabled:
        if st.button("Sign in with Cognito"):
            try:
                login_url = auth.get_login_url()
                st.markdown(f'<meta http-equiv="refresh" content="0;url={login_url}">', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Failed to generate login URL: {str(e)}")
    else:
        st.error("Authentication configuration error")
        if DEV_MODE and st.button("Continue in development mode"):
            st.rerun()

def logout():
    """Handle logout process"""
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.subscription_tier = None
    
    if auth_enabled and not DEV_MODE:
        try:
            logout_url = auth.logout_url()
            st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Logout error: {str(e)}")
            st.rerun()
    else:
        st.rerun()

def process_file(uploaded_file):
    """Process uploaded file with tier restrictions"""
    if not check_upload_limit():
        return

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

            # Clean and format sentences
            st.info("🧹 Formatting text for natural speech...")
            formatted_text = text_processing.clean_and_format_sentences(extracted_text)

            # st.subheader("✅ Final Cleaned Text:")
            # st.write(formatted_text)

            # Handle features with tier checks
            final_text = handle_summarization(formatted_text)
            final_text = handle_translation(final_text)
            handle_speech_conversion(final_text)
            handle_pdf_download(final_text)

            
            increment_upload_count()
            
        finally:
            os.unlink(tmp_path)

def handle_summarization(text):
    """Handle summarization with tier check"""
    if len(text) > 1000:
        if has_feature("Summarization"):
            choice = st.radio("Summarize long text?", ["No", "Yes"])
            if choice == "Yes":
                return comprehend_utils.summarize_text(text)
        else:
            st.warning("🔒 Summarization requires Basic tier or higher")
    return text

def handle_translation(text):
    """Handle translation with tier check"""
    if has_feature("Translation"):
        target_lang = st.selectbox("Translate to:", ["None", "Spanish", "French", "German", "Chinese"])
        lang_map = {"Spanish": "es", "French": "fr", "German": "de", "Chinese": "zh"}
        
        if target_lang != "None":
            translated = translate_utils.translate_text(text, lang_map[target_lang])
            st.subheader("🌐 Translated Text:")
            st.write(translated)
            return translated
    else:
        st.warning("🔒 Translation requires Pro tier")
    return text

def handle_speech_conversion(text):
    """Handle speech conversion with tier check"""
    if has_feature("Speech Conversion"):
        if st.button("🔊 Convert to Speech"):
            audio_url = polly_utils.text_to_speech(text)
            st.audio(audio_url, format="audio/mp3")
    else:
        st.warning("🔒 Speech conversion requires Pro tier")

def handle_pdf_download(text):
    """Handle PDF download with tier check"""
    if has_feature("PDF Download"):
        if st.button("📄 Download PDF"):
            pdf_path = pdf_utils.generate_pdf(text)
            with open(pdf_path, "rb") as f:
                st.download_button("Download PDF", f, "extracted_text.pdf")
            os.remove(pdf_path)
    else:
        st.warning("🔒 PDF download requires Basic tier")

def main_app():
    """Main application interface"""
    st.title("✍ VisionVoice: Handwriting to Voice")
    
    # Sidebar
    st.sidebar.subheader("Account")
    if st.session_state.user_info:
        st.sidebar.write(f"👤 {st.session_state.user_info.get('name', 'User')}")
        st.sidebar.write(f"📧 {st.session_state.user_info.get('email', 'N/A')}")
        st.sidebar.write(f"💎 Tier: {st.session_state.subscription_tier.capitalize()}")
        st.sidebar.write(f"📤 Uploads used: {st.session_state.upload_count}")
    
    if st.sidebar.button("🚪 Logout"):
        logout()
    
    if st.sidebar.button("💰 Manage Subscription"):
        st.session_state.manage_subscription = True
    
    # Subscription management view
    if st.session_state.get("manage_subscription"):
        display_pricing()
        if st.button("← Back to App"):
            st.session_state.manage_subscription = False
            st.rerun()
        return
    
    # Main functionality
    uploaded_file = st.file_uploader("Upload handwritten image", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        process_file(uploaded_file)

def main():
    """Main application flow"""
    initialize_session_state()
    handle_auth_callback()
    
    if st.session_state.authenticated:
        if st.session_state.subscription_tier is None:
            display_pricing()
        else:
            main_app()
    else:
        login_page()

if __name__ == "__main__":
    main()