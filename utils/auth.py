import os
import pickle
import streamlit as st
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import json

# OAuth scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_credentials():
    """Get or refresh Google OAuth credentials for Streamlit Cloud."""
    creds = None
    
    # Check if credentials exist in session state
    if 'google_creds' in st.session_state and st.session_state.google_creds:
        creds = st.session_state.google_creds
        
        # Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                st.session_state.google_creds = creds
                return creds
            except Exception as e:
                st.error(f"Failed to refresh credentials: {e}")
                creds = None
    
    # Try to load saved credentials from secrets
    if not creds:
        try:
            # Check if we have saved refresh token in secrets
            if 'GOOGLE_REFRESH_TOKEN' in st.secrets:
                from google.oauth2.credentials import Credentials
                
                creds = Credentials(
                    None,
                    refresh_token=st.secrets['GOOGLE_REFRESH_TOKEN'],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=st.secrets['GOOGLE_CLIENT_ID'],
                    client_secret=st.secrets['GOOGLE_CLIENT_SECRET'],
                    scopes=SCOPES
                )
                
                # Refresh to get a new access token
                creds.refresh(Request())
                st.session_state.google_creds = creds
                
                # Get user email
                try:
                    service = build('gmail', 'v1', credentials=creds)
                    profile = service.users().getProfile(userId='me').execute()
                    creds.token = {'email': profile.get('emailAddress', 'User')}
                except:
                    creds.token = {'email': 'User'}
                
                return creds
        except Exception as e:
            st.error(f"Failed to load saved credentials: {e}")
    
    # If no saved credentials, start OAuth flow
    if not creds:
        # Create OAuth flow configuration
        client_config = {
            "web": {
                "client_id": st.secrets['GOOGLE_CLIENT_ID'],
                "client_secret": st.secrets['GOOGLE_CLIENT_SECRET'],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost:8501"]
            }
        }
        
        # Display OAuth instructions
        st.warning("⚠️ First-time authentication required")
        
        with st.expander("📋 Authentication Instructions", expanded=True):
            st.markdown("""
            ### How to authenticate:
            
            1. **Get Authorization Code:**
               - Click the link below to authorize the application
               - Sign in with your Google account
               - Grant the requested permissions
               - Copy the authorization code from the redirect URL
               
            2. **Enter the Code:**
               - Paste the authorization code in the text field below
               - Click 'Submit Code' to complete authentication
            """)
            
            # Generate authorization URL
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri="http://localhost:8501"
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            st.markdown(f"🔗 **[Click here to authorize]({auth_url})**")
            
            # Input for authorization code
            auth_code = st.text_input(
                "Enter authorization code:",
                placeholder="Paste the code from the URL after authorization",
                help="After authorizing, you'll be redirected to a URL with '?code=...' - copy everything after 'code='"
            )
            
            if st.button("Submit Code", type="primary"):
                if auth_code:
                    try:
                        # Exchange authorization code for credentials
                        flow.fetch_token(code=auth_code)
                        creds = flow.credentials
                        
                        # Save refresh token to session state
                        st.session_state.google_creds = creds
                        
                        # Get user email
                        try:
                            service = build('gmail', 'v1', credentials=creds)
                            profile = service.users().getProfile(userId='me').execute()
                            creds.token = {'email': profile.get('emailAddress', 'User')}
                        except:
                            creds.token = {'email': 'User'}
                        
                        # Show success message with refresh token
                        st.success("✅ Authentication successful!")
                        
                        # Display refresh token for user to save in secrets
                        st.info("📝 **Important:** Save this refresh token in your Streamlit secrets:")
                        st.code(f"GOOGLE_REFRESH_TOKEN = '{creds.refresh_token}'")
                        st.warning("Add the above line to your Streamlit Cloud secrets to persist authentication")
                        
                        return creds
                        
                    except Exception as e:
                        st.error(f"Failed to authenticate: {str(e)}")
                        st.info("Make sure you copied the complete authorization code")
                else:
                    st.warning("Please enter the authorization code")
        
        return None
    
    return creds
