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
from urllib.parse import parse_qs
from dotenv import load_dotenv
import sys
import traceback

# Load environment variables
load_dotenv()

# Set up development mode - change to True to bypass auth in development
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
    """Initialize session state variables if they don't exist"""
    if "authenticated" not in st.session_state:
        # Auto-authenticate in dev mode
        st.session_state.authenticated = not auth_enabled or DEV_MODE
    if "user_info" not in st.session_state:
        # Mock user info in dev mode
        st.session_state.user_info = {"name": "Developer", "email": "dev@example.com"} if DEV_MODE else None
    if "access_token" not in st.session_state:
        st.session_state.access_token = "dev-token" if DEV_MODE else None

def handle_auth_callback():
    """Handle the OAuth callback after user login"""
    if not auth_enabled or DEV_MODE:
        return
    
    query_params = st.query_params
    print(f"Query params in callback: {dict(query_params)}")  # Debug
    if "code" in query_params:
        try:
            code = query_params["code"]
            # Check for previously processed code to avoid replays
            if "last_processed_code" in st.session_state and st.session_state.last_processed_code == code:
                print(f"Skipping duplicate code: {code}")
                st.query_params.clear()
                return
            
            print(f"OAuth state in session: {st.session_state.get('oauth_state', 'None')}")  # Debug
            
            # Validate state if present
            if "state" in query_params and "oauth_state" in st.session_state and st.session_state.oauth_state:
                if query_params["state"] != st.session_state.oauth_state:
                    print(f"State mismatch: received {query_params['state']}, expected {st.session_state.oauth_state}")
                    raise ValueError("State parameter mismatch")
                print("State validated successfully")
            else:
                print("Skipping state validation: state or oauth_state missing")
                # Optionally store state if received but missing in session
                if "state" in query_params and not st.session_state.get("oauth_state"):
                    print(f"Restoring oauth_state from query: {query_params['state']}")
                    st.session_state.oauth_state = query_params["state"]
            
            print(f"Processing auth callback with code: {code}")  # Debug
            tokens = auth.get_tokens(code)
            st.session_state.access_token = tokens["access_token"]
            
            user_info = auth.get_user_info(tokens["access_token"])
            st.session_state.user_info = user_info
            st.session_state.authenticated = True
            
            # Store the processed code
            st.session_state.last_processed_code = code
            # Clear OAuth state and query params
            st.session_state.oauth_state = None
            st.query_params.clear()
            print("Authentication successful, rerunning app")
            st.rerun()
        except Exception as e:
            print(f"Callback error: {str(e)}")  # Debug
            st.error(f"Authentication error: {str(e)}")
            st.error(traceback.format_exc())
            st.session_state.authenticated = False
            st.session_state.oauth_state = None
            st.query_params.clear()
            st.rerun()

def login_page():
    """Display login page and handle authentication"""
    st.title("✍ VisionVoice: Handwriting to Voice")
    st.header("Login")
    
    st.markdown("You need to log in to use this application.")
    
    if auth_enabled:
        if st.button("Sign in with Cognito"):
            try:
                # Redirect to Cognito login page
                login_url = auth.get_login_url()
                st.markdown(f'<meta http-equiv="refresh" content="0;url={login_url}">', unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Failed to generate login URL: {str(e)}")
                st.error(traceback.format_exc())
    else:
        st.error("Authentication is not configured properly. Please contact the administrator.")
        if DEV_MODE and st.button("Continue in development mode"):
            st.session_state.authenticated = True
            st.rerun()

def logout():
    """Clear session state and redirect to logout URL"""
    # Clear all session state
    st.session_state.authenticated = False
    st.session_state.user_info = None
    st.session_state.access_token = None
    st.session_state.oauth_state = None
    st.session_state.last_processed_code = None  # Clear processed code
    
    if auth_enabled and not DEV_MODE:
        try:
            logout_url = auth.logout_url()
            print(f"Redirecting to logout URL: {logout_url}")  # Debug
            st.markdown(f'<meta http-equiv="refresh" content="0;url={logout_url}">', unsafe_allow_html=True)
        except Exception as e:
            print(f"Logout error: {str(e)}")  # Debug
            st.error(f"Logout error: {str(e)}")
            st.rerun()
    else:
        print("Logging out in dev mode")  # Debug
        st.rerun()

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
            st.success("✅ Here's your audio!")
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

def main_app():
    st.title("✍ VisionVoice: Handwriting to Voice")
    
    # Display user information and logout button in sidebar
    st.sidebar.subheader("User Information")
    if st.session_state.user_info:
        st.sidebar.write(f"Welcome, {st.session_state.user_info.get('name', 'User')}!")
        st.sidebar.write(f"Email: {st.session_state.user_info.get('email', 'N/A')}")
    
    if DEV_MODE:
        st.sidebar.warning("⚠️ Running in development mode")
        
    if st.sidebar.button("Logout"):
        logout()
    
    uploaded_file = st.file_uploader("Upload a handwritten image", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        process_file(uploaded_file)

def main():
    # Initialize session state
    initialize_session_state()
    
    # Handle auth callback if code parameter is present
    handle_auth_callback()
    
    # Show login page or main app based on auth status
    if st.session_state.authenticated:
        main_app()
    else:
        login_page()

if __name__ == "__main__":
    main()