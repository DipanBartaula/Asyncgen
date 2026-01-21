"""
Download VITON Dataset and Upload to S3

Note: The original VITON dataset is no longer publicly available due to copyright issues.
This script uses VITON-HD as an alternative, which is the high-resolution version.
For the original VITON dataset, please refer to download_vtonhd.py

Dataset: VITON-HD (High-Resolution Virtual Try-On)
Source: https://github.com/shadow2496/VITON-HD
Contains: 13,679 image pairs of frontal-view women and top-clothing items (1024x768)
"""

import os
import boto3
import requests
import zipfile
from pathlib import Path
from tqdm import tqdm
from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_REGION

# Configuration
DATASET_NAME = "vton"
DOWNLOAD_URL = "https://drive.google.com/uc?export=download&id=1Uc0DTTkSfCPXDhd4CMx2TQlzlC6Y-Qyc"  # VITON-HD preprocessed
LOCAL_DOWNLOAD_DIR = Path("./datasets_temp/vton")
S3_BASE_PATH = "baselines/vton"

def download_file(url, destination):
    """Download file with progress bar"""
    print(f"Downloading from {url}...")
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(destination, 'wb') as f, tqdm(
        desc=destination.name,
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            pbar.update(size)

def extract_zip(zip_path, extract_to):
    """Extract zip file"""
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"Extracted to {extract_to}")

def upload_to_s3(local_path, s3_path):
    """Upload directory to S3 recursively"""
    print(f"Uploading to S3: {S3_BUCKET_NAME}/{s3_path}")
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=S3_REGION
    )
    
    local_path = Path(local_path)
    
    if local_path.is_file():
        # Upload single file
        s3_key = f"{s3_path}/{local_path.name}"
        print(f"Uploading file: {local_path} -> {s3_key}")
        s3_client.upload_file(str(local_path), S3_BUCKET_NAME, s3_key)
    else:
        # Upload directory recursively
        for file_path in local_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_path)
                s3_key = f"{s3_path}/{relative_path}".replace('\\', '/')
                print(f"Uploading: {relative_path} -> {s3_key}")
                s3_client.upload_file(str(file_path), S3_BUCKET_NAME, s3_key)
    
    print(f"✓ Upload complete!")

def main():
    """Main download and upload pipeline"""
    print("=" * 80)
    print(f"VITON Dataset Download and Upload to S3")
    print("=" * 80)
    
    # Create local directory
    LOCAL_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download dataset
    zip_file = LOCAL_DOWNLOAD_DIR / "viton_hd.zip"
    
    print("\n[1/3] Downloading VITON-HD dataset...")
    print("Note: This uses Google Drive. You may need to manually download if automated download fails.")
    print("Manual download link: https://github.com/shadow2496/VITON-HD")
    
    try:
        download_file(DOWNLOAD_URL, zip_file)
    except Exception as e:
        print(f"Error downloading: {e}")
        print("\nPlease manually download the dataset from:")
        print("https://github.com/shadow2496/VITON-HD")
        print(f"And place it in: {zip_file}")
        input("Press Enter once you've downloaded the file...")
    
    # Extract dataset
    print("\n[2/3] Extracting dataset...")
    extract_dir = LOCAL_DOWNLOAD_DIR / "extracted"
    extract_zip(zip_file, extract_dir)
    
    # Upload to S3
    print("\n[3/3] Uploading to S3...")
    upload_to_s3(extract_dir, S3_BASE_PATH)
    
    print("\n" + "=" * 80)
    print("✓ VITON dataset successfully downloaded and uploaded to S3!")
    print(f"  S3 Location: s3://{S3_BUCKET_NAME}/{S3_BASE_PATH}")
    print("=" * 80)
    
    # Cleanup option
    cleanup = input("\nDelete local files? (y/n): ")
    if cleanup.lower() == 'y':
        import shutil
        shutil.rmtree(LOCAL_DOWNLOAD_DIR)
        print("✓ Local files cleaned up")

if __name__ == "__main__":
    main()
