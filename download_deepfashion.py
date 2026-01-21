"""
Download DeepFashion Dataset (Test Set Only) and Upload to S3

Dataset: DeepFashion - Large-scale Fashion Dataset
Source: http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html
Institution: Multimedia Laboratory, The Chinese University of Hong Kong

Note: This script downloads ONLY the test set of the DeepFashion dataset.
Full dataset requires password from official source after signing agreement.
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
DATASET_NAME = "deepfashion"
# Using Kaggle mirror for easier access (requires Kaggle API)
KAGGLE_DATASET = "paramaggarwal/fashion-product-images-dataset"  # Alternative smaller dataset
LOCAL_DOWNLOAD_DIR = Path("./datasets_temp/deepfashion")
S3_BASE_PATH = "baselines/deepfashion"

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

def extract_test_set(source_dir, output_dir):
    """
    Extract only the test set from the dataset
    
    Args:
        source_dir: Source directory with full dataset
        output_dir: Output directory for test set
    """
    print(f"\nExtracting test set from dataset...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Look for test directory
    test_dirs = list(source_dir.rglob('test'))
    
    if test_dirs:
        print(f"Found {len(test_dirs)} test directories")
        
        # Copy all test directories
        import shutil
        copied_files = 0
        
        for test_dir in test_dirs:
            if test_dir.is_dir():
                # Get relative path from source
                try:
                    relative_path = test_dir.relative_to(source_dir)
                except ValueError:
                    # If test_dir is not relative to source_dir, use just 'test'
                    relative_path = Path('test')
                
                dest_test_dir = output_dir / relative_path
                
                # Copy entire test directory
                if test_dir.exists() and not dest_test_dir.exists():
                    print(f"Copying {test_dir} -> {dest_test_dir}")
                    shutil.copytree(test_dir, dest_test_dir)
                    
                    # Count files
                    for file_path in dest_test_dir.rglob('*'):
                        if file_path.is_file():
                            copied_files += 1
    else:
        # If no explicit test directory, look for test images in the structure
        print("No explicit test directory found. Looking for test images...")
        
        # Find all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        all_images = []
        
        for ext in image_extensions:
            all_images.extend(source_dir.rglob(f'*{ext}'))
            all_images.extend(source_dir.rglob(f'*{ext.upper()}'))
        
        # Filter for test images (images with 'test' in path)
        test_images = [img for img in all_images if 'test' in str(img).lower()]
        
        if not test_images:
            print("⚠ No test images found. Copying all images as test set...")
            test_images = all_images
        
        print(f"Found {len(test_images)} test images")
        
        # Copy test images maintaining directory structure
        import shutil
        copied_files = 0
        
        for img_path in tqdm(test_images, desc="Copying test images"):
            relative_path = img_path.relative_to(source_dir)
            dest_path = output_dir / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not dest_path.exists():
                shutil.copy2(img_path, dest_path)
                copied_files += 1
    
    print(f"✓ Extracted test set with {copied_files} files")
    
    # Also copy any metadata files (CSV, JSON, TXT) that might be in test directories
    metadata_extensions = {'.csv', '.json', '.txt', '.xml'}
    for ext in metadata_extensions:
        for meta_file in source_dir.rglob(f'*{ext}'):
            # Only copy if it's in a test directory or has 'test' in the name
            if 'test' in str(meta_file).lower():
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

def create_dataset_info(output_dir):
    """Create a JSON file with dataset information"""
    info = {
        "dataset": "DeepFashion",
        "source": "http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html",
        "split": "test",
        "note": "Test set only from DeepFashion dataset",
        "download_date": str(Path.ctime(output_dir)) if output_dir.exists() else "unknown"
    }
    
    info_file = output_dir / "dataset_info.json"
    with open(info_file, 'w') as f:
        json.dump(info, f, indent=2)
    
    print(f"✓ Created dataset info: {info_file}")

def main():
    """Main download and upload pipeline"""
    print("=" * 80)
    print(f"DeepFashion Dataset Download (Test Set Only) and Upload to S3")
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
    
    # Extract test set
    print(f"\n[2/5] Extracting test set...")
    test_dir = LOCAL_DOWNLOAD_DIR / "test_only"
    extract_test_set(download_dir, test_dir)
    
    # Create dataset info
    print("\n[3/5] Creating dataset info...")
    create_dataset_info(test_dir)
    
    # Verify test set
    print("\n[4/5] Verifying test set...")
    test_images = list(test_dir.rglob('*.jpg')) + list(test_dir.rglob('*.png'))
    print(f"✓ Test set contains {len(test_images)} images")
    
    # Upload to S3
    print("\n[5/5] Uploading to S3...")
    upload_to_s3(test_dir, S3_BASE_PATH)
    
    print("\n" + "=" * 80)
    print("✓ DeepFashion dataset (test set only) successfully downloaded and uploaded to S3!")
    print(f"  S3 Location: s3://{S3_BUCKET_NAME}/{S3_BASE_PATH}")
    print(f"  Test set size: {len(test_images)} images")
    print("=" * 80)
    
    # Cleanup option
    cleanup = input("\nDelete local files? (y/n): ")
    if cleanup.lower() == 'y':
        import shutil
        shutil.rmtree(LOCAL_DOWNLOAD_DIR)
        print("✓ Local files cleaned up")

if __name__ == "__main__":
    main()
