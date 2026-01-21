"""
Download DressCode Dataset and Upload to S3

Dataset: DressCode - High-Resolution Multi-Category Virtual Try-On
Source: https://github.com/aimagelab/dress-code
Paper: "Dress Code: High-Resolution Multi-Category Virtual Try-On"
Institution: AImageLab, University of Modena and Reggio Emilia

Note: This script downloads only:
- Person images
- Cloth images  
- Segmentation masks

Full dataset requires institutional email and signed agreement.
"""

import os
import boto3
import requests
import zipfile
import json
from pathlib import Path
from tqdm import tqdm
from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_REGION

# Configuration
DATASET_NAME = "dresscode"
# Note: Official dataset requires form submission. Using Hugging Face mirror if available
DATASET_URLS = {
    "images": "https://huggingface.co/datasets/aimagelab/DressCode/resolve/main/DressCode_images.zip",
    "masks": "https://huggingface.co/datasets/aimagelab/DressCode/resolve/main/DressCode_masks.zip"
}
LOCAL_DOWNLOAD_DIR = Path("./datasets_temp/dresscode")
S3_BASE_PATH = "baselines/dresscode"

def download_file(url, destination):
    """Download file with progress bar and resume capability"""
    print(f"Downloading from {url}...")
    
    # Check if file already partially downloaded
    resume_header = {}
    if destination.exists():
        resume_header = {'Range': f'bytes={destination.stat().st_size}-'}
    
    try:
        response = requests.get(url, stream=True, headers=resume_header)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        mode = 'ab' if resume_header else 'wb'
        
        with open(destination, mode) as f, tqdm(
            desc=destination.name,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for data in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                size = f.write(data)
                pbar.update(size)
        
        print(f"✓ Downloaded: {destination}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading: {e}")
        print("\nManual download required:")
        print("1. Visit: https://github.com/aimagelab/dress-code")
        print("2. Fill out the form with institutional email")
        print("3. Download the dataset")
        print(f"4. Place files in: {LOCAL_DOWNLOAD_DIR}")
        return False

def extract_zip(zip_path, extract_to):
    """Extract zip file with progress"""
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.namelist()
        for member in tqdm(members, desc="Extracting"):
            zip_ref.extract(member, extract_to)
    print(f"✓ Extracted to {extract_to}")

def filter_dresscode_files(extract_dir, output_dir):
    """
    Filter DressCode dataset to include only:
    - Person images
    - Cloth images
    - Segmentation masks
    """
    print("\nFiltering dataset (person images, cloth images, segmentation masks only)...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Expected structure: DressCode has categories (dresses, upper_body, lower_body)
    categories = ['dresses', 'upper_body', 'lower_body']
    splits = ['train', 'test']
    
    file_types_to_keep = [
        'images',      # Person images
        'cloth',       # Cloth images
        'label_maps',  # Segmentation masks
        'agnostic-mask',  # Additional masks
    ]
    
    copied_files = 0
    
    for category in categories:
        for split in splits:
            for file_type in file_types_to_keep:
                source_path = extract_dir / category / split / file_type
                
                if source_path.exists():
                    dest_path = output_dir / category / split / file_type
                    dest_path.mkdir(parents=True, exist_ok=True)
                    
                    # Copy files
                    files = list(source_path.glob('*'))
                    for file in tqdm(files, desc=f"{category}/{split}/{file_type}"):
                        if file.is_file():
                            dest_file = dest_path / file.name
                            if not dest_file.exists():
                                import shutil
                                shutil.copy2(file, dest_file)
                                copied_files += 1
    
    print(f"✓ Filtered {copied_files} files")
    return output_dir

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
    
    # Collect all files
    files_to_upload = []
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

def create_dataset_info(output_dir):
    """Create a JSON file with dataset information"""
    info = {
        "dataset": "DressCode",
        "source": "https://github.com/aimagelab/dress-code",
        "categories": ["dresses", "upper_body", "lower_body"],
        "splits": ["train", "test"],
        "included_data": [
            "person_images",
            "cloth_images",
            "segmentation_masks"
        ],
        "note": "Filtered version - only person images, cloth images, and segmentation masks"
    }
    
    info_file = output_dir / "dataset_info.json"
    with open(info_file, 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"✓ Created dataset info: {info_file}")

def main():
    """Main download and upload pipeline"""
    print("=" * 80)
    print(f"DressCode Dataset Download and Upload to S3")
    print("=" * 80)
    
    # Create local directory
    LOCAL_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download dataset
    print("\n[1/5] Downloading DressCode dataset...")
    print("Note: Official dataset requires institutional access.")
    print("Attempting to download from Hugging Face mirror...")
    
    downloaded_files = []
    for name, url in DATASET_URLS.items():
        zip_file = LOCAL_DOWNLOAD_DIR / f"dresscode_{name}.zip"
        if not zip_file.exists():
            success = download_file(url, zip_file)
            if success:
                downloaded_files.append(zip_file)
        else:
            print(f"✓ Already downloaded: {zip_file}")
            downloaded_files.append(zip_file)
    
    if not downloaded_files:
        print("\n⚠ No files downloaded. Please download manually from:")
        print("https://github.com/aimagelab/dress-code")
        return
    
    # Extract dataset
    print("\n[2/5] Extracting dataset...")
    extract_dir = LOCAL_DOWNLOAD_DIR / "extracted"
    extract_dir.mkdir(exist_ok=True)
    
    for zip_file in downloaded_files:
        if zip_file.exists():
            extract_zip(zip_file, extract_dir)
    
    # Filter dataset
    print("\n[3/5] Filtering dataset...")
    filtered_dir = LOCAL_DOWNLOAD_DIR / "filtered"
    filter_dresscode_files(extract_dir, filtered_dir)
    
    # Create dataset info
    print("\n[4/5] Creating dataset info...")
    create_dataset_info(filtered_dir)
    
    # Upload to S3
    print("\n[5/5] Uploading to S3...")
    upload_to_s3(filtered_dir, S3_BASE_PATH)
    
    print("\n" + "=" * 80)
    print("✓ DressCode dataset successfully downloaded and uploaded to S3!")
    print(f"  S3 Location: s3://{S3_BUCKET_NAME}/{S3_BASE_PATH}")
    print(f"  Included: Person images, Cloth images, Segmentation masks")
    print("=" * 80)
    
    # Cleanup option
    cleanup = input("\nDelete local files? (y/n): ")
    if cleanup.lower() == 'y':
        import shutil
        shutil.rmtree(LOCAL_DOWNLOAD_DIR)
        print("✓ Local files cleaned up")

if __name__ == "__main__":
    main()
