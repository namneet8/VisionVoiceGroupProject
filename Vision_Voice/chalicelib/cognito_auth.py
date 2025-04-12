import os
import logging
import streamlit as st
from authlib.integrations.requests_client import OAuth2Session
import requests
import json

class CognitoAuth:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Get Cognito configuration from environment variables
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
        self.client_id = os.getenv('COGNITO_CLIENT_ID')
        self.client_secret = os.getenv('COGNITO_CLIENT_SECRET')
        self.redirect_uri = os.getenv('REDIRECT_URI', 'http://localhost:8501')
        self.metadata = None

        # Initialize endpoints
        self._initialize_endpoints()
        self._validate_metadata()
        
        # Initialize OAuth2 session
        self.oauth = OAuth2Session(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope='openid email profile'
        )

    def _initialize_endpoints(self):
        """Initialize Cognito endpoints with fallback strategies"""
        try:
            self.authority = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            self.metadata_url = f"{self.authority}/.well-known/openid-configuration"
            
            self.logger.info(f"Attempting connection to {self.metadata_url}")
            response = requests.get(self.metadata_url, timeout=5)
            response.raise_for_status()
            self.metadata = response.json()
            self.logger.info("Successfully connected to Cognito IdP endpoint")
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Primary connection failed: {str(e)}")
            self._try_domain_fallback()

    def _try_domain_fallback(self):
        """Attempt domain-based fallback connection"""
        cognito_domain = os.getenv('COGNITO_DOMAIN')
        if not cognito_domain:
            raise ConnectionError("No fallback COGNITO_DOMAIN environment variable set")
            
        domain = f"https://{cognito_domain}.auth.{self.region}.amazoncognito.com"
        try:
            self.logger.info(f"Attempting domain fallback to {domain}")
            response = requests.get(
                f"{domain}/.well-known/openid-configuration", 
                timeout=5
            )
            response.raise_for_status()
            self.metadata = response.json()
            self.logger.info("Successfully connected via domain fallback")
            
        except requests.exceptions.RequestException as domain_error:
            self.logger.warning(f"Domain fallback failed: {str(domain_error)}")
            self.metadata = {
                'authorization_endpoint': f"{domain}/oauth2/authorize",
                'token_endpoint': f"{domain}/oauth2/token",
                'userinfo_endpoint': f"{domain}/oauth2/userInfo",
                'end_session_endpoint': f"{domain}/logout"
            }
            self.logger.warning("Using hardcoded OAuth endpoints")

    def _validate_metadata(self):
        """Validate that all required endpoints exist"""
        required_endpoints = [
            'authorization_endpoint',
            'token_endpoint',
            'userinfo_endpoint',
            'end_session_endpoint'
        ]
        missing = [ep for ep in required_endpoints if ep not in self.metadata]
        if missing:
            self.logger.error(f"Missing required endpoints: {missing}")
            raise ValueError(f"Missing required endpoints: {missing}")

    def get_login_url(self):
        """Generate login URL for Cognito authorization"""
        try:
            url, state = self.oauth.create_authorization_url(
                self.metadata['authorization_endpoint'],
                nonce=os.urandom(16).hex()
            )
            st.session_state.oauth_state = state
            self.logger.info(f"Audit: Login URL generated - State: {state}")
            return url
        except Exception as e:
            self.logger.error(f"Login URL generation failed: {str(e)}", exc_info=True)
            raise RuntimeError("Failed to generate login URL") from e

    def get_tokens(self, code):
        """Exchange authorization code for tokens"""
        try:
            tokens = self.oauth.fetch_token(
                self.metadata['token_endpoint'],
                code=code,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.logger.info("Audit: Successfully obtained access tokens")
            return tokens
        except Exception as e:
            self.logger.error(f"Token exchange failed: {str(e)}", exc_info=True)
            st.session_state.clear()
            raise RuntimeError("Authentication failed") from e

    def get_user_info(self, access_token):
        """Get user info using the access token"""
        try:
            response = requests.get(
                self.metadata['userinfo_endpoint'],
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=5
            )
            response.raise_for_status()
            user_info = response.json()
            user_id = user_info.get('sub', 'UNKNOWN')
            self.logger.info(f"Audit: User info retrieved - User ID: {user_id}")
            return user_info
        except Exception as e:
            self.logger.error(f"User info request failed: {str(e)}", exc_info=True)
            raise RuntimeError("Failed to retrieve user information") from e

    def logout_url(self):
        """Generate URL for logging out the user"""
        try:
            logout_url = (
                f"{self.metadata['end_session_endpoint']}?"
                f"client_id={self.client_id}&"
                f"logout_uri={self.redirect_uri}"
            )
            self.logger.info("Audit: Logout URL generated")
            return logout_url
        except KeyError as e:
            self.logger.error(f"Missing endpoint in metadata: {str(e)}")
            raise RuntimeError("Missing logout endpoint configuration") from e