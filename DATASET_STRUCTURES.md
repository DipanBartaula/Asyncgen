# Dataset Directory Structures

This document provides detailed directory structures for all VTON-related datasets that will be downloaded and stored in the S3 bucket `s3://p1-ep1/baselines/`.

---

## 1. VITON-HD Dataset

**S3 Path**: `s3://p1-ep1/baselines/vtonhd/`

### Directory Structure

```
vtonhd/
├── train/
│   ├── image/                    # Person images (frontal view)
│   │   ├── 000001_00.jpg
│   │   ├── 000002_00.jpg
│   │   └── ... (11,647 images)
│   │
│   ├── cloth/                    # Clothing images (top garments)
│   │   ├── 000001_00.jpg
│   │   ├── 000002_00.jpg
│   │   └── ... (11,647 images)
│   │
│   ├── cloth-mask/               # Binary masks for clothing
│   │   ├── 000001_00.jpg
│   │   ├── 000002_00.jpg
│   │   └── ...
│   │
│   ├── image-parse-v3/           # Human parsing segmentation maps
│   │   ├── 000001_00.png
│   │   ├── 000002_00.png
│   │   └── ...
│   │
│   ├── image-parse-agnostic-v3.2/  # Agnostic person representation
│   │   ├── 000001_00.png
│   │   ├── 000002_00.png
│   │   └── ...
│   │
│   ├── agnostic-v3.2/            # Person with clothing removed
│   │   ├── 000001_00.jpg
│   │   ├── 000002_00.jpg
│   │   └── ...
│   │
│   ├── image-densepose/          # DensePose annotations
│   │   ├── 000001_00.jpg
│   │   ├── 000002_00.jpg
│   │   └── ...
│   │
│   └── openpose_json/            # OpenPose keypoints (JSON)
│       ├── 000001_00_keypoints.json
│       ├── 000002_00_keypoints.json
│       └── ...
│
├── test/
│   ├── image/                    # Person images
│   │   ├── 000001_00.jpg
│   │   └── ... (2,032 images)
│   │
│   ├── cloth/                    # Clothing images
│   │   ├── 000001_00.jpg
│   │   └── ... (2,032 images)
│   │
│   ├── cloth-mask/
│   ├── image-parse-v3/
│   ├── image-parse-agnostic-v3.2/
│   ├── agnostic-v3.2/
│   ├── image-densepose/
│   └── openpose_json/
│
└── train_pairs.txt               # Pairing information (person-cloth pairs)
└── test_pairs.txt

```

### Dataset Statistics
- **Total Images**: 13,679 pairs
- **Train Set**: 11,647 pairs
- **Test Set**: 2,032 pairs
- **Resolution**: 1024 × 768 pixels
- **Format**: JPG (images), PNG (masks/parsing)

### Key Files
- `train_pairs.txt`: Lists person-cloth pairs for training
- `test_pairs.txt`: Lists person-cloth pairs for testing

---

## 2. DressCode Dataset

**S3 Path**: `s3://p1-ep1/baselines/dresscode/`

### Directory Structure

```
dresscode/
├── dresses/                      # Dress category
│   ├── train/
│   │   ├── images/               # Person images wearing dresses
│   │   │   ├── 000001_0.jpg
│   │   │   ├── 000002_0.jpg
│   │   │   └── ...
│   │   │
│   │   ├── cloth/                # Dress garment images
│   │   │   ├── 000001_1.jpg
│   │   │   ├── 000002_1.jpg
│   │   │   └── ...
│   │   │
│   │   ├── label_maps/           # Segmentation masks (person parsing)
│   │   │   ├── 000001_0.png
│   │   │   ├── 000002_0.png
│   │   │   └── ...
│   │   │
│   │   └── agnostic-mask/        # Agnostic person masks
│   │       ├── 000001_0.png
│   │       ├── 000002_0.png
│   │       └── ...
│   │
│   └── test/
│       ├── images/
│       ├── cloth/
│       ├── label_maps/
│       └── agnostic-mask/
│
├── upper_body/                   # Upper body clothing category
│   ├── train/
│   │   ├── images/               # Person images with upper body clothes
│   │   ├── cloth/                # Upper body garment images (shirts, tops, etc.)
│   │   ├── label_maps/           # Segmentation masks
│   │   └── agnostic-mask/
│   │
│   └── test/
│       ├── images/
│       ├── cloth/
│       ├── label_maps/
│       └── agnostic-mask/
│
├── lower_body/                   # Lower body clothing category
│   ├── train/
│   │   ├── images/               # Person images with lower body clothes
│   │   ├── cloth/                # Lower body garment images (pants, skirts, etc.)
│   │   ├── label_maps/           # Segmentation masks
│   │   └── agnostic-mask/
│   │
│   └── test/
│       ├── images/
│       ├── cloth/
│       ├── label_maps/
│       └── agnostic-mask/
│
└── dataset_info.json             # Metadata about the filtered dataset

```

### Dataset Statistics (Full Dataset)
- **Total Images**: ~50,000+ pairs
- **Categories**: 3 (dresses, upper_body, lower_body)
- **Splits**: train, test
- **Resolution**: 1024 × 768 pixels
- **Format**: JPG (images), PNG (masks)

### Filtered Version (Our Download)
**Includes Only**:
- ✅ Person images (`images/`)
- ✅ Cloth images (`cloth/`)
- ✅ Segmentation masks (`label_maps/`)
- ✅ Agnostic masks (`agnostic-mask/`)

**Excludes**:
- ❌ Keypoints
- ❌ Skeletons
- ❌ Dense pose
- ❌ Additional annotations

---

## 3. DeepFashion Dataset (Test Set Only)

**S3 Path**: `s3://p1-ep1/baselines/deepfashion/`

### Directory Structure

```
deepfashion/
├── test/                         # Test set images only
│   ├── images/
│   │   ├── Apparel/
│   │   │   ├── Boys/
│   │   │   │   ├── Images/
│   │   │   │   │   ├── Images/
│   │   │   │   │   │   ├── 1001.jpg
│   │   │   │   │   │   ├── 1002.jpg
│   │   │   │   │   │   └── ...
│   │   │   │
│   │   │   ├── Girls/
│   │   │   ├── Men/
│   │   │   ├── Women/
│   │   │   └── Unisex/
│   │   │
│   │   ├── Accessories/
│   │   ├── Footwear/
│   │   ├── Personal Care/
│   │   └── Free Items/
│   │
│   ├── validation/
│   │   └── (similar structure)
│   │
│   └── test/
│       └── (similar structure)
│
├── styles.csv                    # Metadata: product IDs, categories, colors, etc.
├── styles_corrected.csv          # Corrected metadata
├── dataset_info.json             # Information about the 20% subset
└── README.txt                    # Dataset description

```

### Alternative Structure (DeepFashion2)

```
deepfashion/
├── train/
│   ├── image/                    # Training images
│   │   ├── 000001.jpg
│   │   ├── 000002.jpg
│   │   └── ... (20% subset)
│   │
│   └── annos/                    # Annotations (JSON)
│       ├── 000001.json
│       ├── 000002.json
│       └── ...
│
├── validation/
│   ├── image/
│   └── annos/
│
├── test/
│   └── image/                    # Test images (no annotations)
│
└── dataset_info.json

```

### Dataset Statistics (Test Set)
- **Original Dataset**: ~800,000 images
- **Test Set**: Contains test split only
- **Categories**: Multiple (Apparel, Accessories, Footwear, etc.)
- **Format**: JPG (images), CSV/JSON (metadata)

### Metadata Fields (styles.csv)
- `id`: Product ID
- `gender`: Target gender
- `masterCategory`: Main category
- `subCategory`: Sub-category
- `articleType`: Specific article type
- `baseColour`: Primary color
- `season`: Fashion season
- `year`: Year of release
- `usage`: Usage type
- `productDisplayName`: Product name

---

## 4. VTON Dataset (Legacy)

**S3 Path**: `s3://p1-ep1/baselines/vton/`

**Note**: The original VITON dataset is no longer publicly available due to copyright issues. The download script uses VITON-HD as an alternative.

### Expected Structure (if available)

```
vton/
├── train/
│   ├── person/                   # Person images
│   ├── cloth/                    # Clothing images
│   ├── person_parse/             # Parsing maps
│   └── cloth_mask/               # Cloth masks
│
├── test/
│   ├── person/
│   ├── cloth/
│   ├── person_parse/
│   └── cloth_mask/
│
└── train_pairs.txt
└── test_pairs.txt

```

---

## S3 Bucket Organization

### Complete Baselines Structure

```
s3://p1-ep1/
└── baselines/
    ├── vton/                     # VITON (uses VITON-HD)
    │   └── (VITON-HD structure)
    │
    ├── vtonhd/                   # VITON-HD
    │   ├── train/
    │   ├── test/
    │   └── *.txt
    │
    ├── dresscode/                # DressCode (filtered)
    │   ├── dresses/
    │   ├── upper_body/
    │   ├── lower_body/
    │   └── dataset_info.json
    │
    └── deepfashion/              # DeepFashion (test set only)
        ├── test/
        ├── styles.csv (if available)
        └── dataset_info.json

```

---

## File Naming Conventions

### VITON-HD
- **Person images**: `{id}_00.jpg` (e.g., `000001_00.jpg`)
- **Cloth images**: `{id}_00.jpg` (same ID as paired person)
- **Masks/Parsing**: `{id}_00.png`
- **Keypoints**: `{id}_00_keypoints.json`

### DressCode
- **Person images**: `{id}_0.jpg` (e.g., `000001_0.jpg`)
- **Cloth images**: `{id}_1.jpg` (e.g., `000001_1.jpg`)
- **Masks**: `{id}_0.png`

### DeepFashion
- **Images**: `{id}.jpg` (e.g., `1001.jpg`)
- **Annotations**: `{id}.json`

---

## Data Loading Examples

### VITON-HD Pair Loading

```python
# Read pairs file
with open('train_pairs.txt', 'r') as f:
    pairs = f.readlines()

# Each line format: person_image cloth_image
# Example: 000001_00.jpg 000001_00.jpg

for pair in pairs:
    person_img, cloth_img = pair.strip().split()
    person_path = f"train/image/{person_img}"
    cloth_path = f"train/cloth/{cloth_img}"
    mask_path = f"train/image-parse-v3/{person_img.replace('.jpg', '.png')}"
```

### DressCode Category Loading

```python
categories = ['dresses', 'upper_body', 'lower_body']
split = 'train'

for category in categories:
    images_dir = f"{category}/{split}/images/"
    cloth_dir = f"{category}/{split}/cloth/"
    masks_dir = f"{category}/{split}/label_maps/"
```

### DeepFashion Metadata Loading

```python
import pandas as pd

# Load metadata
styles_df = pd.read_csv('styles.csv')

# Filter by category
women_apparel = styles_df[
    (styles_df['gender'] == 'Women') & 
    (styles_df['masterCategory'] == 'Apparel')
]

# Get image path
image_id = women_apparel.iloc[0]['id']
image_path = f"images/train/Apparel/Women/Images/Images/{image_id}.jpg"
```

---

## Important Notes

### Resolution Standards
- **VITON-HD**: 1024 × 768 (high-resolution)
- **DressCode**: 1024 × 768 (high-resolution)
- **DeepFashion**: Variable (typically 400-800px)

### Image Formats
- **RGB Images**: JPG/JPEG
- **Masks/Parsing**: PNG (grayscale or indexed color)
- **Annotations**: JSON, TXT, CSV

### Pairing Information
- **VITON-HD**: Explicit pairs in `train_pairs.txt`, `test_pairs.txt`
- **DressCode**: Implicit pairing via filename IDs
- **DeepFashion**: Metadata-based (no explicit person-cloth pairs)

### Storage Estimates
- **VITON-HD**: ~15-20 GB
- **DressCode (filtered)**: ~10-15 GB
- **DeepFashion (test set)**: ~2-5 GB
- **Total**: ~27-40 GB

---

## References

- **VITON-HD**: [GitHub](https://github.com/shadow2496/VITON-HD)
- **DressCode**: [GitHub](https://github.com/aimagelab/dress-code)
- **DeepFashion**: [Project Page](http://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html)
