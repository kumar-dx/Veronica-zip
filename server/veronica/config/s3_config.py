"""AWS S3 configuration settings"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

def get_store_name():
    """
    Fetch store name from API
    Returns:
        str: Store name formatted for S3 path (lowercase, hyphenated)
    """
    try:
        api_endpoint = os.getenv("API_ENDPOINT_BASE_URL")
        store_id = os.getenv("STORE_ID")
        api_key = os.getenv("API_KEY")

        if not all([api_endpoint, store_id, api_key]):
            raise ValueError("Missing required API configuration")

        response = requests.get(
            f"{api_endpoint}/api/v1/analytics/stores/?store_id={store_id}",
            headers={
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success' and data.get('data', {}).get('name'):
                return data['data']['name'].replace(" ", "-").lower()
        
        raise ValueError(f"Failed to fetch store name: {response.text}")
    except Exception as e:
        print(json.dumps({
            "type": "error",
            "data": f"Error fetching store name: {str(e)}"
        }), flush=True)
        return "default-store"  # Fallback name

# Initialize store name
STORE_NAME = get_store_name()

# S3 configuration
S3_CONFIG = {
    "bucket_name": os.getenv("AWS_BUCKET_NAME"),
    "aws_access_key": os.getenv("AWS_ACCESS_KEY_ID"),
    "aws_secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "region": os.getenv("AWS_REGION"),
    "base_prefix": STORE_NAME  # Use fetched store name as base prefix
}

def get_daily_prefix():
    """
    Generate S3 prefix with daily folder structure
    Returns:
        str: Prefix path in format: base_prefix/YYYY/MM/DD/
    """
    base_prefix = S3_CONFIG["base_prefix"].rstrip('/')
    today = datetime.now()
    date_path = today.strftime("%Y/%m/%d")
    return f"{base_prefix}/{date_path}/"

def validate_s3_config():
    """Validate that all required S3 configuration values are present"""
    missing_vars = []
    for key, value in S3_CONFIG.items():
        if value is None and key != "base_prefix":  # base_prefix is optional
            missing_vars.append(key)
    
    if missing_vars:
        raise ValueError(
            f"Missing required S3 configuration variables: {', '.join(missing_vars)}. "
            "Please copy sample.env to .env and set the required values."
        )
