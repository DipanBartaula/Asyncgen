# Dataset Download Scripts

This directory contains scripts to download VTON-related datasets and upload them to S3 bucket `p1-ep1` under the `baselines` directory.

## Available Scripts

### 1. `download_vton.py`
Downloads the VITON-HD dataset (original VITON is no longer available).
- **Dataset**: VITON-HD
- **Source**: https://github.com/shadow2496/VITON-HD
- **Size**: 13,679 image pairs (1024x768)
- **S3 Path**: `s3://p1-ep1/baselines/vton/`

### 2. `download_vtonhd.py`
Downloads the VITON-HD dataset with enhanced verification.
- **Dataset**: VITON-HD (High-Resolution Virtual Try-On)
- **Source**: Google Drive via official repo
- **Size**: 13,679 image pairs (1024x768)
- **S3 Path**: `s3://p1-ep1/baselines/vtonhd/`
- **Features**: Automatic structure verification, progress tracking

### 3. `download_dresscode.py`
Downloads DressCode dataset (filtered version).
- **Dataset**: DressCode Multi-Category Virtual Try-On
- **Source**: https://github.com/aimagelab/dress-code
- **Included Data**:
  - Person images
  - Cloth images
  - Segmentation masks only
- **Categories**: dresses, upper_body, lower_body
- **S3 Path**: `s3://p1-ep1/baselines/dresscode/`

### 4. `download_deepfashion.py`
Downloads the test set only from DeepFashion dataset.
- **Dataset**: DeepFashion (Test set only)
- **Source**: Kaggle alternative (official requires institutional access)
- **Split**: Test set only
- **S3 Path**: `s3://p1-ep1/baselines/deepfashion/`

## Prerequisites

### Required Python Packages
```bash
pip install boto3 requests tqdm gdown kaggle
```

### AWS Configuration
Ensure your `src/config.py` has valid AWS credentials:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME` (default: "p1-ep1")
- `S3_REGION` (default: "us-east-1")

### Kaggle API (for DeepFashion)
1. Go to https://www.kaggle.com/settings
2. Create new API token
3. Place `kaggle.json` in:
   - Linux/Mac: `~/.kaggle/`
   - Windows: `C:\Users\<User>\.kaggle\`

## Usage

### Basic Usage
```bash
# Download VITON-HD
python download_vtonhd.py

# Download DressCode
python download_dresscode.py

# Download DeepFashion (test set only)
python download_deepfashion.py
```

### What Each Script Does
1. **Downloads** the dataset to a temporary local directory (`./datasets_temp/`)
2. **Extracts** compressed files (if applicable)
3. **Filters** data (for DressCode and DeepFashion)
4. **Uploads** to S3 bucket under `baselines/<dataset_name>/`
5. **Cleanup** option to delete local files after upload

## S3 Directory Structure

After running all scripts, your S3 bucket will have:

```
s3://p1-ep1/
└── baselines/
    ├── vton/
    │   ├── train/
    │   └── test/
    ├── vtonhd/
    │   ├── train/
    │   └── test/
    ├── dresscode/
    │   ├── dresses/
    │   ├── upper_body/
    │   ├── lower_body/
    │   └── dataset_info.json
    └── deepfashion/
        ├── images/
        └── dataset_info.json
```

## Manual Download Notes

### VITON-HD
If automated download fails:
- Visit: https://github.com/shadow2496/VITON-HD
- Download the preprocessed dataset
- Place in `./datasets_temp/vtonhd/viton_hd.zip`
- Re-run the script

### DressCode
Official dataset requires institutional email:
- Visit: https://github.com/aimagelab/dress-code
- Fill out the form
- Download and place in `./datasets_temp/dresscode/`

### DeepFashion
Official dataset requires signed agreement:
- Visit: http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html
- Alternative: https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset

## Troubleshooting

### Google Drive Download Issues
If `gdown` fails for VITON-HD:
```bash
pip install --upgrade gdown
```

### S3 Upload Errors
- Check AWS credentials in `src/config.py`
- Verify S3 bucket exists and you have write permissions
- Check region settings

### Disk Space
Ensure sufficient disk space:
- VITON-HD: ~15GB
- DressCode: ~20GB
- DeepFashion: ~5GB (for 20% subset)

## Features

- ✅ **Resume capability**: Downloads can be resumed if interrupted
- ✅ **Progress tracking**: Real-time progress bars for downloads and uploads
- ✅ **Verification**: Dataset structure verification before upload
- ✅ **Metadata**: JSON files with dataset information
- ✅ **Cleanup**: Optional local file cleanup after upload
- ✅ **Error handling**: Graceful fallback to manual download instructions

## Notes

- All scripts maintain the original dataset structure
- Filtered datasets include metadata JSON files
- Random sampling for DeepFashion uses seed=42 for reproducibility
- Scripts are idempotent - safe to re-run
