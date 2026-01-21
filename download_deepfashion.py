"""
Download DeepFashion Dataset (20% Subset) and Upload to S3

Dataset: DeepFashion - Large-scale Fashion Dataset
Source: http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html
Institution: Multimedia Laboratory, The Chinese University of Hong Kong

Note: This script downloads a 20% subset of the DeepFashion dataset.
Full dataset requires password from official source after signing agreement.
"""

import os
import boto3
import requests
import zipfile
import json
import random
from pathlib import Path
from tqdm import tqdm
from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME, S3_REGION

# Configuration
DATASET_NAME = "deepfashion"
# Using Kaggle mirror for easier access (requires Kaggle API)
KAGGLE_DATASET = "paramaggarwal/fashion-product-images-dataset"  # Alternative smaller dataset
LOCAL_DOWNLOAD_DIR = Path("./datasets_temp/deepfashion")
S3_BASE_PATH = "baselines/deepfashion"
SUBSET_PERCENTAGE = 0.20  # 20% subset

def download_with_kaggle(dataset_name, destination_dir):
    """Download dataset from Kaggle using kaggle API"""
    print(f"Downloading from Kaggle: {dataset_name}")
    
    try:
        import kaggle
        kaggle.api.dataset_download_files(
            dataset_name,
            path=str(destination_dir),
            unzip=True,
            quiet=False
        )
        print(f"✓ Downloaded to {destination_dir}")
        return True
    except ImportError:
        print("Kaggle API not installed. Installing...")
        os.system("pip install kaggle")
        print("\nPlease configure Kaggle API:")
        print("1. Go to https://www.kaggle.com/settings")
        print("2. Create new API token")
        print("3. Place kaggle.json in ~/.kaggle/ (Linux/Mac) or C:\\Users\\<User>\\.kaggle\\ (Windows)")
        return False
    except Exception as e:
        print(f"Error downloading from Kaggle: {e}")
        return False

def download_file(url, destination):
    """Download file with progress bar"""
    print(f"Downloading from {url}...")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destination, 'wb') as f, tqdm(
            desc=destination.name,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for data in response.iter_content(chunk_size=1024*1024):
                size = f.write(data)
                pbar.update(size)
        
        print(f"✓ Downloaded: {destination}")
        return True
        
    except Exception as e:
        print(f"Error downloading: {e}")
        return False

def create_subset(source_dir, output_dir, percentage=0.20):
    """
    Create a random subset of the dataset
    
    Args:
        source_dir: Source directory with full dataset
        output_dir: Output directory for subset
        percentage: Percentage of data to include (0.20 = 20%)
    """
    print(f"\nCreating {percentage*100}% subset of dataset...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    all_images = []
    
    for ext in image_extensions:
        all_images.extend(source_dir.rglob(f'*{ext}'))
        all_images.extend(source_dir.rglob(f'*{ext.upper()}'))
    
    print(f"Found {len(all_images)} total images")
    
    # Random sample
    random.seed(42)  # For reproducibility
    subset_size = int(len(all_images) * percentage)
    subset_images = random.sample(all_images, subset_size)
    
    print(f"Selected {subset_size} images for subset")
    
    # Copy subset maintaining directory structure
    copied_files = 0
    for img_path in tqdm(subset_images, desc="Copying subset"):
        relative_path = img_path.relative_to(source_dir)
        dest_path = output_dir / relative_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not dest_path.exists():
            import shutil
            shutil.copy2(img_path, dest_path)
            copied_files += 1
    
    print(f"✓ Created subset with {copied_files} images")
    
    # Also copy any metadata files (CSV, JSON, TXT)
    metadata_extensions = {'.csv', '.json', '.txt', '.xml'}
    for ext in metadata_extensions:
        for meta_file in source_dir.rglob(f'*{ext}'):
            relative_path = meta_file.relative_to(source_dir)
            dest_path = output_dir / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not dest_path.exists():
                import shutil
                shutil.copy2(meta_file, dest_path)
    
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

def create_dataset_info(output_dir, subset_percentage):
    """Create a JSON file with dataset information"""
    info = {
        "dataset": "DeepFashion",
        "source": "http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html",
        "subset_percentage": subset_percentage * 100,
        "note": f"Random {subset_percentage*100}% subset of DeepFashion dataset",
        "seed": 42,
        "download_date": str(Path.ctime(output_dir)) if output_dir.exists() else "unknown"
    }
    
    info_file = output_dir / "dataset_info.json"
    with open(info_file, 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"✓ Created dataset info: {info_file}")

def main():
    """Main download and upload pipeline"""
    print("=" * 80)
    print(f"DeepFashion Dataset Download (20% Subset) and Upload to S3")
    print("=" * 80)
    
    # Create local directory
    LOCAL_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download dataset
    print("\n[1/5] Downloading DeepFashion dataset...")
    print("Note: Using Kaggle fashion dataset as alternative.")
    print("For official DeepFashion, visit: http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html")
    
    download_dir = LOCAL_DOWNLOAD_DIR / "full"
    download_dir.mkdir(exist_ok=True)
    
    # Try Kaggle download
    success = download_with_kaggle(KAGGLE_DATASET, download_dir)
    
    if not success:
        print("\n⚠ Automated download failed. Manual download options:")
        print("1. Official DeepFashion: http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html")
        print("2. Kaggle alternative: https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset")
        print(f"3. Place downloaded files in: {download_dir}")
        input("\nPress Enter once you've downloaded the dataset...")
    
    # Check if we have any data
    image_files = list(download_dir.rglob('*.jpg')) + list(download_dir.rglob('*.png'))
    if not image_files:
        print("⚠ No images found in download directory!")
        return
    
    print(f"✓ Found {len(image_files)} images in dataset")
    
    # Create subset
    print(f"\n[2/5] Creating {SUBSET_PERCENTAGE*100}% subset...")
    subset_dir = LOCAL_DOWNLOAD_DIR / "subset_20pct"
    create_subset(download_dir, subset_dir, SUBSET_PERCENTAGE)
    
    # Create dataset info
    print("\n[3/5] Creating dataset info...")
    create_dataset_info(subset_dir, SUBSET_PERCENTAGE)
    
    # Verify subset
    print("\n[4/5] Verifying subset...")
    subset_images = list(subset_dir.rglob('*.jpg')) + list(subset_dir.rglob('*.png'))
    print(f"✓ Subset contains {len(subset_images)} images")
    
    # Upload to S3
    print("\n[5/5] Uploading to S3...")
    upload_to_s3(subset_dir, S3_BASE_PATH)
    
    print("\n" + "=" * 80)
    print("✓ DeepFashion dataset (20% subset) successfully downloaded and uploaded to S3!")
    print(f"  S3 Location: s3://{S3_BUCKET_NAME}/{S3_BASE_PATH}")
    print(f"  Subset size: {len(subset_images)} images ({SUBSET_PERCENTAGE*100}% of original)")
    print("=" * 80)
    
    # Cleanup option
    cleanup = input("\nDelete local files? (y/n): ")
    if cleanup.lower() == 'y':
        import shutil
        shutil.rmtree(LOCAL_DOWNLOAD_DIR)
        print("✓ Local files cleaned up")

if __name__ == "__main__":
    main()
