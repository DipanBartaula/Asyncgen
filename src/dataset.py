import torch
from torch.utils.data import Dataset
import boto3
import json
import logging
from PIL import Image
from io import BytesIO
import os

try:
    from src.config import S3_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
except ImportError:
    # Fallback if running outside of package context
    S3_REGION = os.getenv("S3_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

logger = logging.getLogger(__name__)

class S3VTONDataset(Dataset):
    def __init__(self, jsonl_paths, transform=None, s3_bucket=None):
        """
        Args:
            jsonl_paths (list): List of S3 keys or local paths to JSONL files.
            transform (callable, optional): PyTorch transforms for images.
            s3_bucket (str, optional): Default bucket name if s3:// path doesn't specify.
        """
        self.transform = transform
        self.data = []
        self.s3_client = None # Lazy init per worker
        
        # 1. Parse JSONL Data immediately (Metadata fits in RAM)
        self._load_metadata(jsonl_paths)
        
    def _init_s3(self):
        # Initialize boto3 client per-worker to avoid fork safety issues
        if self.s3_client is None:
            self.s3_client = boto3.client(
                's3',
                region_name=S3_REGION,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY
            )

    def _load_metadata(self, jsonl_paths):
        # Initialize a temporary client just for metadata loading
        temp_client = boto3.client(
            's3',
            region_name=S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
        
        for path in jsonl_paths:
            print(f"Loading metadata from {path}...")
            
            # Helper to split bucket/key from s3:// or direct key
            bucket, key = self._parse_s3_path(path)
            
            try:
                obj = temp_client.get_object(Bucket=bucket, Key=key)
                content = obj['Body'].read().decode('utf-8')
                
                lines = content.strip().split('\n')
                for line in lines:
                    if not line.strip(): continue
                    item = json.loads(line)
                    self.data.append(item)
                    
            except Exception as e:
                logger.error(f"Failed to load JSONL {path}: {e}")
                
        print(f"Loaded {len(self.data)} training samples.")

    def _parse_s3_path(self, path):
        """
        Parses s3://bucket/key or just key if default bucket provided.
        Returns (bucket, key)
        """
        if path.startswith("s3://"):
            # s3://bucket/key/path...
            path_no_scheme = path[5:]
            parts = path_no_scheme.split('/', 1)
            return parts[0], parts[1]
        else:
            # Assume local path or relative s3 key? 
            # This class assumes S3 usage.
            # If path structure is implied, user must pass bucket explicitly elsewhere
            # But based on vton_main.py, paths are s3://
             raise ValueError(f"Expected s3:// path, got {path}")

    def _download_image(self, s3_uri):
        bucket, key = self._parse_s3_path(s3_uri)
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            image_data = response['Body'].read()
            image = Image.open(BytesIO(image_data)).convert('RGB')
            return image
        except Exception as e:
            logger.error(f"Error downloading {s3_uri}: {e}")
            return None

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        self._init_s3() # Ensure client exists
        
        item = self.data[idx]
        
        # Format: { "initial_image": ..., "cloth_image": ..., "try_on_image": ... }
        
        person_uri = item['initial_image']
        cloth_uri = item['cloth_image']
        target_uri = item['try_on_image']
        
        person_img = self._download_image(person_uri)
        cloth_img = self._download_image(cloth_uri)
        target_img = self._download_image(target_uri)
        
        # Handle failures (return None or empty tensor? usually skip)
        # In simple implementation we might error out.
        if person_img is None or cloth_img is None or target_img is None:
             # Logic to retrieve another random item or fail
             # For simplicity, fail noisily
             raise RuntimeError(f"Failed to load images for index {idx}")

        if self.transform:
            person_img = self.transform(person_img)
            cloth_img = self.transform(cloth_img)
            target_img = self.transform(target_img)
            
        return {
            "initial_image": person_img,
            "cloth_image": cloth_img,
            "try_on_image": target_img
        }
