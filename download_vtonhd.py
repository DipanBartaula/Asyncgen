"""
Download VITON-HD Dataset and Upload to S3

Dataset: VITON-HD (High-Resolution Virtual Try-On)
Source: https://github.com/shadow2496/VITON-HD
Paper: "VITON-HD: High-Resolution Virtual Try-On via Misalignment-Aware Normalization"
Contains: 13,679 image pairs of frontal-view women and top-clothing items
Resolution: 1024x768 pixels
"""

import os
import boto3
import requests
import zipfile
import gdown
from pathlib import Path
from tqdm import tqdm
from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_REGION

# Configuration
DATASET_NAME = "vtonhd"
# Google Drive file ID for VITON-HD preprocessed dataset
GDRIVE_FILE_ID = "1Uc0DTTkSfCPXDhd4CMx2TQlzlC6Y-Qyc"
LOCAL_DOWNLOAD_DIR = Path("./datasets_temp/vtonhd")
S3_BASE_PATH = "baselines/vtonhd"

def download_from_gdrive(file_id, destination):
    """Download file from Google Drive using gdown"""
    print(f"Downloading VITON-HD from Google Drive...")
    url = f"https://drive.google.com/uc?id={file_id}"
    
    try:
        gdown.download(url, str(destination), quiet=False)
        print(f"✓ Downloaded to {destination}")
    except Exception as e:
        print(f"Error with gdown: {e}")
        print("\nAlternative: Please manually download from:")
        print("https://github.com/shadow2496/VITON-HD")
        print(f"And place the zip file at: {destination}")
        input("Press Enter once you've downloaded the file...")

def extract_zip(zip_path, extract_to):
    """Extract zip file with progress"""
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.namelist()
        for member in tqdm(members, desc="Extracting"):
            zip_ref.extract(member, extract_to)
    print(f"✓ Extracted to {extract_to}")

def upload_to_s3(local_path, s3_path):
    """Upload directory to S3 recursively with progress"""
    print(f"Uploading to S3: s3://{S3_BUCKET_NAME}/{s3_path}")
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=S3_REGION
    )
    
    local_path = Path(local_path)
    
    # Collect all files first
    files_to_upload = []
    if local_path.is_file():
        files_to_upload.append((local_path, local_path.name))
    else:
        for file_path in local_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_path)
                files_to_upload.append((file_path, relative_path))
    
    # Upload with progress bar
    print(f"Found {len(files_to_upload)} files to upload")
    for file_path, relative_path in tqdm(files_to_upload, desc="Uploading to S3"):
        s3_key = f"{s3_path}/{relative_path}".replace('\\', '/')
        s3_client.upload_file(str(file_path), S3_BUCKET_NAME, s3_key)
    
    print(f"✓ Upload complete!")

def verify_dataset_structure(extract_dir):
    """Verify the dataset has expected structure"""
    print("\nVerifying dataset structure...")
    expected_dirs = ['train', 'test']
    
    for split in expected_dirs:
        split_dir = extract_dir / split
        if split_dir.exists():
            print(f"✓ Found {split} split")
            # Count files in subdirectories
            for subdir in split_dir.iterdir():
                if subdir.is_dir():
                    file_count = len(list(subdir.glob('*')))
                    print(f"  - {subdir.name}: {file_count} files")
        else:
            print(f"⚠ Warning: {split} split not found")

def main():
    """Main download and upload pipeline"""
    print("=" * 80)
    print(f"VITON-HD Dataset Download and Upload to S3")
    print("=" * 80)
    
    # Create local directory
    LOCAL_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download dataset
    zip_file = LOCAL_DOWNLOAD_DIR / "viton_hd.zip"
    
    print("\n[1/4] Downloading VITON-HD dataset...")
    if not zip_file.exists():
        download_from_gdrive(GDRIVE_FILE_ID, zip_file)
    else:
        print(f"✓ Zip file already exists: {zip_file}")
    
    # Extract dataset
    print("\n[2/4] Extracting dataset...")
    extract_dir = LOCAL_DOWNLOAD_DIR / "extracted"
    if not extract_dir.exists():
        extract_zip(zip_file, extract_dir)
    else:
        print(f"✓ Already extracted: {extract_dir}")
    
    # Verify structure
    print("\n[3/4] Verifying dataset structure...")
    verify_dataset_structure(extract_dir)
    
    # Upload to S3
    print("\n[4/4] Uploading to S3...")
    upload_to_s3(extract_dir, S3_BASE_PATH)
    
    print("\n" + "=" * 80)
    print("✓ VITON-HD dataset successfully downloaded and uploaded to S3!")
    print(f"  S3 Location: s3://{S3_BUCKET_NAME}/{S3_BASE_PATH}")
    print(f"  Dataset: 13,679 image pairs (1024x768)")
    print("=" * 80)
    
    # Cleanup option
    cleanup = input("\nDelete local files? (y/n): ")
    if cleanup.lower() == 'y':
        import shutil
        shutil.rmtree(LOCAL_DOWNLOAD_DIR)
        print("✓ Local files cleaned up")

if __name__ == "__main__":
    # Check if gdown is installed
    try:
        import gdown
    except ImportError:
        print("Installing gdown for Google Drive downloads...")
        os.system("pip install gdown")
        import gdown
    
    main()
