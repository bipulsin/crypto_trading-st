# Google OAuth Configuration for Trade Manthan
# This file contains the OAuth credentials and configuration

import os

# Google OAuth Configuration
GOOGLE_CLIENT_ID = "your-google-client-id-here"
GOOGLE_CLIENT_SECRET = "your-google-client-secret-here"

# OAuth Redirect URIs
GOOGLE_REDIRECT_URI = "https://trademanthan.in/callback"
GOOGLE_REDIRECT_URI_HTTP = "http://trademanthan.in/callback"

# OAuth Scopes
GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

# OAuth Configuration Dictionary
OAUTH_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": [GOOGLE_REDIRECT_URI, GOOGLE_REDIRECT_URI_HTTP]
    }
}

# Environment variables for the application
ENV_VARS = {
    "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
    "GOOGLE_REDIRECT_URI": GOOGLE_REDIRECT_URI,
    "FLASK_SECRET_KEY": "your-production-secret-key-change-this-in-production"
}

def get_oauth_config():
    """Get OAuth configuration with environment variable fallback"""
    return {
        "client_id": os.environ.get('GOOGLE_CLIENT_ID', GOOGLE_CLIENT_ID),
        "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET', GOOGLE_CLIENT_SECRET),
        "redirect_uri": os.environ.get('GOOGLE_REDIRECT_URI', GOOGLE_REDIRECT_URI)
    }

def print_setup_instructions():
    """Print setup instructions for OAuth configuration"""
    print("=" * 60)
    print("GOOGLE OAUTH SETUP INSTRUCTIONS")
    print("=" * 60)
    print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable Google+ API and Google OAuth2 API")
    print("4. Go to Credentials > Create Credentials > OAuth 2.0 Client ID")
    print("5. Set Application Type to 'Web application'")
    print("6. Add Authorized redirect URIs:")
    print(f"   - {GOOGLE_REDIRECT_URI}")
    print(f"   - {GOOGLE_REDIRECT_URI_HTTP}")
    print("7. Copy the Client ID and Client Secret")
    print("8. Update this file with your credentials")
    print("9. Or set environment variables:")
    print(f"   export GOOGLE_CLIENT_ID='your-client-id'")
    print(f"   export GOOGLE_CLIENT_SECRET='your-client-secret'")
    print("=" * 60)

if __name__ == "__main__":
    print_setup_instructions()
