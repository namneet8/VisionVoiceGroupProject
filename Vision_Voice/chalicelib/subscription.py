import streamlit as st
import boto3
from datetime import datetime, timedelta

# AWS Cognito client
cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

TIERS = {
    "free": {"name": "Free", "cost": 0, "upload_limit": 5, "features": ["Text Extraction"]},
    "basic": {"name": "Basic", "cost": 9, "upload_limit": 50, "features": ["Text Extraction", "Summarization", "PDF Download"]},
    "pro": {"name": "Pro", "cost": 19, "upload_limit": 200, "features": ["Text Extraction", "Summarization", "Translation", "Speech Conversion", "PDF Download"]},
    "enterprise": {"name": "Enterprise", "cost": 49, "upload_limit": float('inf'), "features": ["All Features", "Priority Processing"]}
}

def fetch_subscription_tier(username):
    """Fetch user's subscription tier from Cognito"""
    try:
        response = cognito_client.admin_get_user(
            UserPoolId="us-east-1_xdDAqKLlX",
            Username=username
        )
        for attr in response["UserAttributes"]:
            if attr["Name"] == "custom:subscription_tier":
                return attr["Value"]
        return None  # Return None if not set
    except Exception as e:
        st.error(f"Error fetching subscription: {str(e)}")
        return None

def update_subscription_tier(username, tier):
    """Update subscription tier in Cognito"""
    try:
        cognito_client.admin_update_user_attributes(
            UserPoolId="us-east-1_xdDAqKLlX",
            Username=username,
            UserAttributes=[{"Name": "custom:subscription_tier", "Value": tier}]
        )
        st.session_state.subscription_tier = tier
        st.session_state.upload_count = 0
        st.session_state.last_reset = datetime.now().isoformat()
        st.success(f"Subscribed to {TIERS[tier]['name']} tier!")
    except Exception as e:
        st.error(f"Subscription update failed: {str(e)}")

def display_pricing():
    """Show subscription options"""
    st.title("📊 Choose Your Plan")
    
    cols = st.columns(4)
    tiers = list(TIERS.keys())
    
    for i, tier in enumerate(tiers):
        with cols[i]:
            st.subheader(TIERS[tier]["name"])
            st.write(f"${TIERS[tier]['cost']}/mo")
            st.write(f"Uploads: {TIERS[tier]['upload_limit']}")
            st.write("Features:")
            for feature in TIERS[tier]["features"]:
                st.write(f"- {feature}")
                
            if st.session_state.subscription_tier == tier:
                st.button("Current Plan", key=tier, disabled=True)
            else:
                if st.button(f"Choose {TIERS[tier]['name']}", key=tier):
                    update_subscription_tier(st.session_state.user_info["username"], tier)
                    st.rerun()

def check_upload_limit():
    """Enforce monthly upload limits"""
    if "last_reset" not in st.session_state:
        st.session_state.last_reset = datetime.now().isoformat()
    
    time_diff = datetime.now() - datetime.fromisoformat(st.session_state.last_reset)
    if time_diff > timedelta(days=30):
        st.session_state.upload_count = 0
        st.session_state.last_reset = datetime.now().isoformat()
    
    tier = TIERS[st.session_state.subscription_tier or "free"]
    if st.session_state.get("upload_count", 0) >= tier["upload_limit"]:
        st.error(f"❗ {tier['name']} tier limit reached. Upgrade to continue.")
        return False
    return True

def increment_upload_count():
    """Track upload usage"""
    st.session_state.upload_count = st.session_state.get("upload_count", 0) + 1

def has_feature(feature):
    """Check feature availability"""
    tier = st.session_state.subscription_tier or "free"
    return feature in TIERS[tier]["features"]