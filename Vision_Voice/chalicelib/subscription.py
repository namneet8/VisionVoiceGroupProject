import streamlit as st
import boto3
import logging
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, BotoCoreError

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        logger.info(f"Audit: Fetching subscription tier for user: {username}")
        response = cognito_client.admin_get_user(
            UserPoolId="us-east-1_xdDAqKLlX",
            Username=username
        )
        for attr in response["UserAttributes"]:
            if attr["Name"] == "custom:subscription_tier":
                logger.info(f"Audit: Subscription tier found for user {username} - Tier: {attr['Value']}")
                return attr["Value"]
        logger.warning(f"No subscription tier set for user {username}")
        return None
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error fetching subscription tier for {username} - {e}", exc_info=True)
        st.error("Error fetching subscription tier. Please try again.")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in fetch_subscription_tier - {e}", exc_info=True)
        st.error("Unexpected error while checking subscription.")
        return None

def update_subscription_tier(username, tier):
    """Update subscription tier in Cognito"""
    try:
        logger.info(f"Audit: Updating subscription tier for {username} to {tier}")
        cognito_client.admin_update_user_attributes(
            UserPoolId="us-east-1_xdDAqKLlX",
            Username=username,
            UserAttributes=[{"Name": "custom:subscription_tier", "Value": tier}]
        )
        st.session_state.subscription_tier = tier
        st.session_state.upload_count = 0
        st.session_state.last_reset = datetime.now().isoformat()
        st.success(f"Subscribed to {TIERS[tier]['name']} tier!")
        logger.info(f"Audit: Subscription updated successfully for user {username}")
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error updating subscription tier for {username} - {e}", exc_info=True)
        st.error("Subscription update failed. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error in update_subscription_tier - {e}", exc_info=True)
        st.error("Unexpected error during subscription update.")

def display_pricing():
    """Show subscription options"""
    try:
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
    except Exception as e:
        logger.error(f"Error displaying pricing - {e}", exc_info=True)
        st.error("Failed to load pricing information.")

def check_upload_limit():
    """Enforce monthly upload limits"""
    try:
        if "last_reset" not in st.session_state:
            st.session_state.last_reset = datetime.now().isoformat()

        time_diff = datetime.now() - datetime.fromisoformat(st.session_state.last_reset)
        if time_diff > timedelta(days=30):
            st.session_state.upload_count = 0
            st.session_state.last_reset = datetime.now().isoformat()
            logger.info("Audit: Monthly upload limit reset")

        tier_key = st.session_state.subscription_tier or "free"
        tier = TIERS[tier_key]

        if st.session_state.get("upload_count", 0) >= tier["upload_limit"]:
            logger.warning(f"Upload limit reached for tier: {tier_key}")
            st.error(f"❗ {tier['name']} tier limit reached. Upgrade to continue.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error in check_upload_limit - {e}", exc_info=True)
        st.error("Unexpected error while checking upload limit.")
        return False

def increment_upload_count():
    """Track upload usage"""
    try:
        st.session_state.upload_count = st.session_state.get("upload_count", 0) + 1
        logger.info(f"Audit: Upload count incremented - New count: {st.session_state.upload_count}")
    except Exception as e:
        logger.error(f"Error incrementing upload count - {e}", exc_info=True)

def has_feature(feature):
    """Check feature availability"""
    try:
        tier = st.session_state.subscription_tier or "free"
        has_it = feature in TIERS[tier]["features"]
        logger.info(f"Audit: Feature check - Tier: {tier}, Feature: {feature}, Available: {has_it}")
        return has_it
    except Exception as e:
        logger.error(f"Error checking feature access - {e}", exc_info=True)
        return False
