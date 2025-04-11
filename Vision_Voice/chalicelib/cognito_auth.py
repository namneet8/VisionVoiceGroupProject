import os
import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
import requests
import json

class CognitoAuth:
    def __init__(self):
        # Get Cognito configuration from environment variables
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        self.client_id = os.getenv('COGNITO_CLIENT_ID')
        self.client_secret = os.getenv('COGNITO_CLIENT_SECRET')
        self.redirect_uri = os.getenv('REDIRECT_URI', 'http://localhost:8501')
        
        # Use the correct endpoint format based on AWS example
        self.authority = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
        self.metadata_url = f"{self.authority}/.well-known/openid-configuration"
        
        print(f"Connecting to Cognito at: {self.metadata_url}")
        
        try:
            response = requests.get(self.metadata_url, timeout=5)
            response.raise_for_status()
            self.metadata = response.json()
            print("Successfully connected to Cognito IdP endpoint")
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Cognito IdP endpoint: {str(e)}")
            
            # Try the domain-based approach as fallback
            cognito_domain = os.getenv('COGNITO_DOMAIN')
            if cognito_domain:
                domain = f"https://{cognito_domain}.auth.{self.region}.amazoncognito.com"
                try:
                    # Try to see if we can connect to the domain endpoint
                    print(f"Trying fallback to domain endpoint: {domain}")
                    response = requests.get(f"{domain}/.well-known/openid-configuration", timeout=5)
                    response.raise_for_status()
                    self.metadata = response.json()
                    print("Successfully connected to Cognito domain endpoint")
                except requests.exceptions.RequestException as domain_error:
                    print(f"Error connecting to domain endpoint: {str(domain_error)}")
                    # Use standard OAuth endpoints for Cognito as a last resort
                    self.metadata = {
                        'authorization_endpoint': f"{domain}/oauth2/authorize",
                        'token_endpoint': f"{domain}/oauth2/token",
                        'userinfo_endpoint': f"{domain}/oauth2/userInfo", 
                        'end_session_endpoint': f"{domain}/logout"
                    }
                    print(f"Using fallback metadata: {json.dumps(self.metadata, indent=2)}")
            else:
                raise ConnectionError(f"Failed to connect to Cognito: {str(e)}")
            
        # Initialize OAuth2 session
        self.oauth = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope='openid email profile'
        )

    def get_login_url(self):
        """Generate login URL for Cognito authorization"""
        url, state = self.oauth.create_authorization_url(
            self.metadata['authorization_endpoint'],
            nonce=os.urandom(16).hex()
        )
        st.session_state.oauth_state = state
        print(f"Generated login URL: {url}")  # Debug
        print(f"Stored oauth_state: {state}")  # Debug
        print(f"Session state after setting: {st.session_state.get('oauth_state', 'None')}")  # Debug
        return url

    def get_tokens(self, code):
        """Exchange authorization code for tokens"""
        try:
            # Use the proper fetch_token method
            tokens = self.oauth.fetch_token(
                self.metadata['token_endpoint'],
                code=code,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            print("Successfully fetched tokens")
            return tokens
        except Exception as e:
            print(f"Error fetching tokens: {str(e)}")
            raise

    def get_user_info(self, access_token):
        """Get user info using the access token"""
        try:
            response = requests.get(
                self.metadata['userinfo_endpoint'],
                headers={'Authorization': f'Bearer {access_token}'}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching user info: {str(e)}")
            raise

    def logout_url(self):
        """Generate URL for logging out the user"""
        logout_url = (
            f"{self.metadata['end_session_endpoint']}?"
            f"client_id={self.client_id}&"
            f"logout_uri={self.redirect_uri}"
        )
        print(f"Generated logout URL: {logout_url}")  # Debug
        return logout_url