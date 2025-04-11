import os
import requests
import json
from dotenv import load_dotenv

def test_cognito_domain():
    # Load environment variables
    load_dotenv()
    
    # Get domain and region
    domain_prefix = os.getenv('COGNITO_DOMAIN')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    if not domain_prefix:
        print("❌ ERROR: COGNITO_DOMAIN environment variable not set!")
        return False
    
    # Construct domain URL
    domain = f"https://{domain_prefix}.auth.{region}.amazoncognito.com"
    print(f"Testing connection to Cognito domain: {domain}")
    
    # Test basic domain connection
    try:
        response = requests.get(domain, timeout=5)
        print(f"✅ Basic domain connection successful: Status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Failed to connect to domain: {str(e)}")
        print("\nPossible issues:")
        print("1. The domain prefix may be incorrect")
        print("2. The Cognito domain has not been set up")
        print("3. There might be network connectivity issues")
        return False
    
    # Test OpenID configuration
    metadata_url = f'{domain}/.well-known/openid-configuration'
    print(f"\nTesting metadata URL: {metadata_url}")
    
    try:
        response = requests.get(metadata_url, timeout=5)
        if response.status_code == 200:
            metadata = response.json()
            print(f"✅ Successfully retrieved OpenID configuration")
            print(f"\nEndpoints found:")
            for key in ['authorization_endpoint', 'token_endpoint', 'userinfo_endpoint']:
                if key in metadata:
                    print(f"  - {key}: {metadata[key]}")
            return True
        else:
            print(f"❌ ERROR: Metadata request failed: Status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Failed to retrieve metadata: {str(e)}")
        return False
    except json.JSONDecodeError:
        print(f"❌ ERROR: Failed to parse metadata as JSON")
        return False

if __name__ == "__main__":
    print("=== Cognito Connection Test ===")
    result = test_cognito_domain()
    
    if result:
        print("\n✅ SUCCESS: Cognito domain is correctly configured and accessible")
    else:
        print("\n❌ FAILED: Cognito domain test failed")
        print("\nSuggested actions:")
        print("1. Verify your Cognito User Pool has a domain set up in the AWS Console")
        print("2. Check that the COGNITO_DOMAIN in your .env file matches the domain prefix in AWS")
        print("3. Make sure your network can reach AWS Cognito services")