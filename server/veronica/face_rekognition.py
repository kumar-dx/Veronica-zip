import os
import json
import boto3
import requests
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

class FaceDetector:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.rekognition_client = boto3.client(
            'rekognition',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = os.getenv('AWS_BUCKET_NAME')

    def list_images(self) -> List[str]:
        """List images from current date using pagination"""
        from datetime import datetime
        
        # Get store data for the prefix
        store_data = self.get_store_data()
        if not store_data or not store_data.get('data', {}).get('name'):
            print(json.dumps({
                "type": "error",
                "data": "Failed to get store name for S3 prefix"
            }), flush=True)
            return []
            
        # Format store name for S3 path
        store_name = store_data['data']['name'].replace(" ", "-").lower()
        
        # Generate today's prefix
        today = datetime.now()
        date_prefix = today.strftime("%Y/%m/%d")
        
        # Combine store name with date prefix
        full_prefix = f"{store_name}/{date_prefix}/"
        
        print(json.dumps({
            "type": "info",
            "data": f"Fetching images for date: {today.strftime('%Y-%m-%d')}"
        }), flush=True)
        
        images = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=full_prefix
            ):
                if 'Contents' in page:
                    images.extend(obj['Key'] for obj in page['Contents'])
            
            print(json.dumps({
                "type": "info",
                "data": f"Found {len(images)} images for today"
            }), flush=True)
            
            return images
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error listing today's images: {str(e)}"
            }), flush=True)
            return []

    def detect_faces(self, image_key: str) -> List[Dict]:
        """Detect faces in a single image."""
        try:
            print(json.dumps({
                "type": "info",
                "data": f"Detecting faces in image: {image_key}"
            }), flush=True)
            
            response = self.rekognition_client.detect_faces(
                Image={
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': image_key
                    }
                }
            )
            
            faces = response.get('FaceDetails', [])
            print(json.dumps({
                "type": "info",
                "data": f"Found {len(faces)} faces in image"
            }), flush=True)
            return faces
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error detecting faces: {str(e)}"
            }), flush=True)
            return []

    def compare_faces(self, source_image: str, target_image: str) -> bool:
        """Compare faces between two images."""
        try:
            print(json.dumps({
                "type": "info",
                "data": f"Comparing faces: {source_image} vs {target_image}"
            }), flush=True)
            
            response = self.rekognition_client.compare_faces(
                SourceImage={
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': source_image
                    }
                },
                TargetImage={
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': target_image
                    }
                },
                SimilarityThreshold=80.0
            )
            
            matches = len(response.get('FaceMatches', [])) > 0
            print(json.dumps({
                "type": "info",
                "data": "Face match found" if matches else "No face match found"
            }), flush=True)
            return matches
            
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error comparing faces: {str(e)}"
            }), flush=True)
            return False

    def find_unique_faces(self) -> List[Dict]:
        """Find unique faces across all images."""
        print(json.dumps({
            "type": "info",
            "data": "Starting unique face detection process"
        }), flush=True)
        
        images = self.list_images()
        if not images:
            print(json.dumps({
                "type": "info",
                "data": "No images to process"
            }), flush=True)
            return []

        # Store groups of matching faces
        face_groups = []
        total_images = len(images)
        
        for i, image in enumerate(images, 1):
            print(json.dumps({
                "type": "info",
                "data": f"Processing image {i}/{total_images}"
            }), flush=True)
            
            faces = self.detect_faces(image)
            if not faces:
                continue

            # For each face in the current image
            for _ in faces:
                matched = False
                
                # Compare with existing groups
                for group in face_groups:
                    # Compare with the first image in the group
                    if self.compare_faces(group['source_image'], image):
                        group['faces'].append({
                            'image': image
                        })
                        matched = True
                        break
                
                # If no match found, create new group
                if not matched:
                    face_groups.append({
                        'source_image': image,
                        'faces': [{
                            'image': image
                        }]
                    })
                    print(json.dumps({
                        "type": "info",
                        "data": "New unique face found"
                    }), flush=True)

        print(json.dumps({
            "type": "info",
            "data": f"Found {len(face_groups)} unique faces"
        }), flush=True)
        return face_groups


    def get_store_data(self):
        """Fetch store details from API using the store ID from environment variables."""
        store_id = os.getenv("STORE_ID")
        base_url = os.getenv("API_ENDPOINT_BASE_URL")
        
        if not store_id:
            print(json.dumps({
                "type": "error",
                "data": "STORE_ID not found in environment variables"
            }), flush=True)
            return None

        try:
            response = requests.get(f"{base_url}/api/v1/analytics/stores/?store_id={store_id}", headers={'X-API-KEY': os.getenv('API_KEY')})
            response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)

            store_data = response.json()
            return store_data if store_data else None  # Return store data if available
        except requests.RequestException as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error fetching store details: {str(e)}"
            }), flush=True)
            return None

    def post_count(self, count: int) -> bool:
        """Post the count of unique faces to the API endpoint."""
        api_endpoint = os.getenv('API_ENDPOINT_BASE_URL')
        if not api_endpoint:
            print(json.dumps({
                "type": "error",
                "data": "API_ENDPOINT_BASE_URL environment variable not set"
            }), flush=True)
            return False
        
        # Load store data
        store_data = self.get_store_data()
        if not store_data:
            print(json.dumps({
                "type": "error",
                "data": "No store data available"
            }), flush=True)
            return False
        
        try:
            print(json.dumps({
                "type": "info",
                "data": f"Posting count to API: {count} unique faces"
            }), flush=True)
            
            # Prepare payload with integer values
            payload = {
                'unique_faces_count': count,
                'store_id': os.getenv('STORE_ID'),
                'store_name': store_data["data"]["name"]
            }
            print(json.dumps({
                "type": "info",
                "data": f"Sending payload to API: {payload}"
            }), flush=True)
            
            try:
                response = requests.post(
                    f"{api_endpoint}/api/v1/analytics/visitors/",
                    json=payload,
                    headers={'Content-Type': 'application/json', 'X-API-KEY': os.getenv('API_KEY')}
                )
                response.raise_for_status()
                
                # Log response for debugging
                print(json.dumps({
                    "type": "info",
                    "data": f"API Response: {response.status_code} {response.text}"
                }), flush=True)
                
            except requests.exceptions.HTTPError as e:
                # Log detailed error info
                print(json.dumps({
                    "type": "error",
                    "data": f"API Error Response: {e.response.status_code} {e.response.text}"
                }), flush=True)
                raise
            
            print(json.dumps({
                "type": "info",
                "data": "Successfully posted count to API"
            }), flush=True)
            return True
            
        except requests.exceptions.RequestException as e:
            print(json.dumps({
                "type": "error",
                "data": f"Error posting count to API: {str(e)}"
            }), flush=True)
            return False

def main():
    try:
        # Force stdout to be unbuffered
        import sys
        import io
        sys.stdout = io.TextIOWrapper(
            open(sys.stdout.fileno(), 'wb', 0),
            write_through=True
        )
        
        print(json.dumps({
            "type": "info",
            "data": "Starting face recognition process..."
        }), flush=True)
        
        # Validate S3 configuration
        from config.s3_config import validate_s3_config
        try:
            validate_s3_config()
            print(json.dumps({
                "type": "info",
                "data": "S3 configuration validated successfully"
            }), flush=True)
        except ValueError as e:
            print(json.dumps({
                "type": "error",
                "data": f"S3 configuration error: {str(e)}"
            }), flush=True)
            return
        
        # Initialize detector with validation
        try:
            detector = FaceDetector()
            print(json.dumps({
                "type": "info",
                "data": "Face detector initialized successfully"
            }), flush=True)
        except Exception as e:
            print(json.dumps({
                "type": "error",
                "data": f"Failed to initialize face detector: {str(e)}"
            }), flush=True)
            return
        unique_faces = detector.find_unique_faces()
        count = len(unique_faces)
        
        if detector.post_count(count):
            print(json.dumps({
                "type": "success",
                "data": f"Successfully processed {count} unique faces"
            }), flush=True)
        else:
            print(json.dumps({
                "type": "error",
                "data": f"Failed to post count to API. Count was: {count}"
            }), flush=True)
            
    except Exception as e:
        print(json.dumps({
            "type": "error",
            "data": f"Face recognition error: {str(e)}"
        }), flush=True)

if __name__ == "__main__":
    main()
