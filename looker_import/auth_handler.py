"""
Google API authentication handler for Looker Studio, BigQuery, and Google Sheets.

Supports:
- Service Account authentication
- OAuth 2.0 user consent flow
- Token caching and refresh
"""

import os
import json
import pickle
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


class GoogleAuthHandler:
    """Manages Google API authentication."""
    
    def __init__(self, credentials_dir: str = '.credentials'):
        """
        Initialize auth handler.
        
        Args:
            credentials_dir: Directory to store credentials and tokens
        """
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(exist_ok=True)
        self.service_account_path = self.credentials_dir / 'service-account.json'
        self.oauth_token_path = self.credentials_dir / 'oauth-token.pickle'
        self.oauth_credentials_path = self.credentials_dir / 'oauth-credentials.json'
    
    def setup_service_account(self, json_path: str) -> bool:
        """
        Setup service account authentication.
        
        Args:
            json_path: Path to service account JSON file
            
        Returns:
            True if setup successful
        """
        try:
            # Copy service account JSON
            with open(json_path, 'r') as f:
                credentials = json.load(f)
            
            with open(self.service_account_path, 'w') as f:
                json.dump(credentials, f)
            
            print(f"✓ Service account configured: {self.service_account_path}")
            
            # Validate required fields
            required = ['type', 'project_id', 'private_key', 'client_email']
            for field in required:
                if field not in credentials:
                    print(f"✗ Missing field: {field}")
                    return False
            
            return True
        
        except Exception as e:
            print(f"✗ Setup failed: {e}")
            return False
    
    def get_service_account_credentials(self):
        """Get service account credentials object."""
        try:
            from google.oauth2 import service_account
            
            if not self.service_account_path.exists():
                raise FileNotFoundError("Service account JSON not found. Run --auth first.")
            
            credentials = service_account.Credentials.from_service_account_file(
                str(self.service_account_path),
                scopes=[
                    'https://www.googleapis.com/auth/datastudio',
                    'https://www.googleapis.com/auth/bigquery',
                    'https://www.googleapis.com/auth/spreadsheets',
                ]
            )
            
            return credentials
        
        except ImportError:
            print("✗ google-auth library not installed. Run: pip install google-auth google-auth-oauthlib")
            return None
        except Exception as e:
            print(f"✗ Failed to get credentials: {e}")
            return None
    
    def setup_oauth(self, client_id: str = None, client_secret: str = None) -> bool:
        """
        Setup OAuth 2.0 authentication.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            
        Returns:
            True if setup successful
        """
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            if not client_id or not client_secret:
                print("OAuth setup requires client_id and client_secret")
                return False
            
            # Create OAuth credentials config
            oauth_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]
                }
            }
            
            with open(self.oauth_credentials_path, 'w') as f:
                json.dump(oauth_config, f)
            
            # Start OAuth flow
            scopes = [
                'https://www.googleapis.com/auth/datastudio',
                'https://www.googleapis.com/auth/bigquery',
                'https://www.googleapis.com/auth/spreadsheets',
            ]
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.oauth_credentials_path),
                scopes
            )
            
            credentials = flow.run_local_server(port=0)
            
            # Save token
            with open(self.oauth_token_path, 'wb') as f:
                pickle.dump(credentials, f)
            
            print(f"✓ OAuth token saved: {self.oauth_token_path}")
            return True
        
        except ImportError:
            print("✗ google-auth-oauthlib not installed. Run: pip install google-auth-oauthlib")
            return False
        except Exception as e:
            print(f"✗ OAuth setup failed: {e}")
            return False
    
    def get_oauth_credentials(self):
        """Get OAuth credentials from cached token."""
        try:
            if not self.oauth_token_path.exists():
                raise FileNotFoundError("OAuth token not found. Run --auth oauth first.")
            
            with open(self.oauth_token_path, 'rb') as f:
                credentials = pickle.load(f)
            
            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
            
            return credentials
        
        except Exception as e:
            print(f"✗ Failed to get OAuth credentials: {e}")
            return None
    
    def interactive_setup(self) -> bool:
        """Interactive setup wizard."""
        print("\n🔐 Google API Setup Wizard")
        print("=" * 50)
        
        choice = input("\nChoose authentication method:\n1. Service Account (recommended)\n2. OAuth 2.0\nChoice (1-2): ").strip()
        
        if choice == '1':
            json_path = input("Path to service-account.json: ").strip()
            return self.setup_service_account(json_path)
        
        elif choice == '2':
            client_id = input("OAuth Client ID: ").strip()
            client_secret = input("OAuth Client Secret: ").strip()
            return self.setup_oauth(client_id, client_secret)
        
        else:
            print("Invalid choice")
            return False
    
    def is_configured(self) -> Tuple[bool, str]:
        """Check if authentication is configured."""
        if self.service_account_path.exists():
            return True, "service_account"
        elif self.oauth_token_path.exists():
            return True, "oauth"
        else:
            return False, "none"


class CredentialsManager:
    """Manages credential storage and lifecycle."""
    
    def __init__(self, auth_handler: GoogleAuthHandler):
        self.auth_handler = auth_handler
        self.service_account_credentials = None
        self.oauth_credentials = None
    
    def get_credentials(self, method: str = 'auto'):
        """
        Get appropriate credentials.
        
        Args:
            method: 'service_account', 'oauth', or 'auto'
            
        Returns:
            Google credentials object
        """
        if method == 'auto':
            is_configured, auth_type = self.auth_handler.is_configured()
            if not is_configured:
                raise ValueError("No credentials configured. Run: python migrate.py --auth")
            method = auth_type
        
        if method == 'service_account':
            return self.auth_handler.get_service_account_credentials()
        elif method == 'oauth':
            return self.auth_handler.get_oauth_credentials()
        else:
            raise ValueError(f"Unknown auth method: {method}")
    
    def validate_credentials(self) -> bool:
        """Validate that credentials are valid."""
        try:
            is_configured, auth_type = self.auth_handler.is_configured()
            if not is_configured:
                return False
            
            credentials = self.get_credentials(auth_type)
            return credentials is not None
        except Exception as e:
            print(f"✗ Credential validation failed: {e}")
            return False
