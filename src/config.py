import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# S3 Configuration
# WARNING: Hardcoded credentials. In production, use environment variables or IAM roles.
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "p1-to-ep1")
S3_REGION = os.getenv("S3_REGION", "ap-south-1")
S3_PREFIX = os.getenv("S3_PREFIX", "generated_images")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Run Configuration
# OUTPUT_BASE_DIR = Path("output")
# OUTPUT_BASE_DIR.mkdir(exist_ok=True)

# Hugging Face Auth
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if HUGGINGFACE_TOKEN:
    try:
        from huggingface_hub import login
        print(f"Logging in to Hugging Face Hub...")
        login(token=HUGGINGFACE_TOKEN)
        print("✓ Successfully logged in to Hugging Face.")
    except ImportError:
        print("Warning: huggingface_hub not installed. Cannot login.")
    except Exception as e:
        print(f"Warning: Failed to login to Hugging Face: {e}")
