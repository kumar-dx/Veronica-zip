"""AWS S3 utilities for uploading files"""

import os
import time
import json
import boto3
import botocore
from config.s3_config import S3_CONFIG, get_daily_prefix

class S3Uploader:
    def __init__(self):
        """Initialize S3 client with credentials from config"""
        self.enabled = False
        self.max_retries = 3
        self.retry_delay = 1
        
        try:
            if not all(S3_CONFIG.values()):
                raise ValueError("Missing required S3 configuration values")
                
            # Initialize S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=S3_CONFIG['aws_access_key'],
                aws_secret_access_key=S3_CONFIG['aws_secret_key'],
                region_name=S3_CONFIG['region']
            )
            self.bucket_name = S3_CONFIG['bucket_name']
            
            # Verify bucket exists and is accessible
            try:
                self.s3_client.head_bucket(Bucket=self.bucket_name)
                self.enabled = True
                print(json.dumps({
                    "type": "info",
                    "data": f"Successfully connected to S3 bucket: {self.bucket_name}"
                }), flush=True)
            except botocore.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    raise ValueError(f"Bucket {self.bucket_name} does not exist")
                elif error_code == '403':
                    raise ValueError(f"Access denied to bucket {self.bucket_name}")
                else:
                    raise
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"S3 upload disabled: {str(e)}"
            }), flush=True)
        
    def upload_file(self, file_path, s3_path=None):
        """
        Upload a file to S3 if enabled, otherwise keep locally
        Args:
            file_path (str): Local path to the file
            s3_path (str, optional): S3 path/key. If None, uses the filename
        Returns:
            str: S3 URL of the uploaded file if successful, None otherwise
        """
        if not self.enabled:
            print(json.dumps({
                "type": "info",
                "data": f"S3 upload disabled - file saved locally at: {file_path}"
            }), flush=True)
            return None
            
        if not os.path.exists(file_path):
            print(json.dumps({
                "type": "error",
                "data": f"Error: File not found at {file_path}"
            }), flush=True)
            return None
            
        # If s3_path not provided, use filename only
        # If s3_path not provided, use filename with daily prefix
        if s3_path is None:
            filename = file_path.split('/')[-1]
            s3_path = os.path.join(get_daily_prefix(), filename).replace('\\', '/')
        else:
            # If s3_path is provided, ensure it's under the daily prefix
            s3_path = os.path.join(get_daily_prefix(), s3_path).replace('\\', '/')
            
        retries = 0
        while retries < self.max_retries:
            try:
                # Upload file
                self.s3_client.upload_file(
                    file_path,
                    self.bucket_name,
                    s3_path
                )
                
                # Verify upload by checking if file exists
                try:
                    self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=s3_path
                    )
                    # Generate S3 URL
                    url = f"https://{self.bucket_name}.s3.{S3_CONFIG['region']}.amazonaws.com/{s3_path}"
                    print(json.dumps({
                        "type": "info",
                        "data": f"Successfully uploaded to S3: {url}"
                    }), flush=True)
                    return url
                except botocore.exceptions.ClientError:
                    print(json.dumps({
                        "type": "error",
                        "data": "Upload verification failed"
                    }), flush=True)
                    raise
                    
            except Exception as e:
                retries += 1
                if retries < self.max_retries:
                    print(json.dumps({
                        "type": "error",
                        "data": f"Upload attempt {retries} failed: {str(e)}"
                    }), flush=True)
                    print(json.dumps({
                        "type": "info",
                        "data": f"Retrying in {self.retry_delay} seconds..."
                    }), flush=True)
                    time.sleep(self.retry_delay)
                else:
                    print(json.dumps({
                        "type": "error",
                        "data": f"Failed to upload after {self.max_retries} attempts: {str(e)}"
                    }), flush=True)
                    return None
