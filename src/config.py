import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# S3 Configuration
# WARNING: Hardcoded credentials. In production, use environment variables or IAM roles.
# AWS Credentials
# You can hardcode them here OR use environment variables.
_ACCESS_KEY = "YOUR_AWS_ACCESS_KEY"
_SECRET_KEY = "YOUR_AWS_SECRET_KEY"

# If user hasn't replaced the placeholder, try loading from environment
if _ACCESS_KEY == "YOUR_AWS_ACCESS_KEY":
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
else:
    AWS_ACCESS_KEY_ID = _ACCESS_KEY

if _SECRET_KEY == "YOUR_AWS_SECRET_KEY":
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
else:
    AWS_SECRET_ACCESS_KEY = _SECRET_KEY

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
