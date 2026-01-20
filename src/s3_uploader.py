import os
import asyncio
import aioboto3
from PIL import Image
from io import BytesIO
from src.config import S3_BUCKET_NAME, S3_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

class AsyncUploader:
    def __init__(self):
        self.session = aioboto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=S3_REGION
        )
    
    async def upload_data(self, image: Image.Image, text_content: str, gender: str, prompt_number: str):
        """
        Uploads image and text to S3 asynchronously using gender/images and gender/prompts structure.
        """
        # Ensure gender is lowercase/clean
        gender = gender.lower().strip()
        
        print(f"Starting upload for {gender} Prompt {prompt_number}...")
        try:
            async with self.session.client("s3", region_name=S3_REGION) as s3:
                # 1. Upload Image -> gender/images/number.png
                img_buffer = BytesIO()
                image.save(img_buffer, format="PNG")
                img_buffer.seek(0)
                
                image_key = f"{gender}/images/{prompt_number}.png"
                await s3.upload_fileobj(img_buffer, S3_BUCKET_NAME, image_key)
                
                # 2. Upload Text -> gender/prompts/number.txt
                text_key = f"{gender}/prompts/{prompt_number}.txt"
                await s3.put_object(Body=text_content.encode('utf-8'), Bucket=S3_BUCKET_NAME, Key=text_key)
                
                print(f"✓ Successfully uploaded {gender}/{prompt_number} to S3.")
                
        except Exception as e:
            print(f"❌ Error uploading {gender}/{prompt_number}: {e}")

    async def download_image(self, key: str) -> Image.Image:
        """
        Downloads an image from S3 and returns a PIL Image object.
        """
        try:
            async with self.session.client("s3", region_name=S3_REGION) as s3:
                response = await s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
                image_data = await response['Body'].read()
                return Image.open(BytesIO(image_data)).convert("RGB")
        except Exception as e:
            print(f"Error downloading image {key}: {e}")
            return None

    async def download_text(self, key: str) -> str:
        """
        Downloads a text file from S3 and returns its content string.
        """
        try:
            async with self.session.client("s3", region_name=S3_REGION) as s3:
                response = await s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
                text_data = await response['Body'].read()
                return text_data.decode('utf-8')
        except Exception as e:
            print(f"Error downloading text {key}: {e}")
            return None

    async def upload_edited_image(self, image: Image.Image, key: str):
        """
        Uploads the edited image to the specified S3 key.
        """
        # print(f"Uploading edited image to {key}...")
        try:
            async with self.session.client("s3", region_name=S3_REGION) as s3:
                img_buffer = BytesIO()
                image.save(img_buffer, format="PNG")
                img_buffer.seek(0)
                await s3.upload_fileobj(img_buffer, S3_BUCKET_NAME, key)
                print(f"✓ Uploaded: {key}")
        except Exception as e:
            print(f"❌ Error uploading edited image {key}: {e}")

    async def check_exists(self, key: str) -> bool:
        """
        Checks if a file exists in S3.
        """
        try:
             async with self.session.client("s3", region_name=S3_REGION) as s3:
                await s3.head_object(Bucket=S3_BUCKET_NAME, Key=key)
                return True
        except:
            return False

    async def get_existing_prompts(self, gender: str) -> set:
        """
        Scan S3 for existing images in {gender}/images/ to support resuming.
        Returns a set of prompt numbers (strings) that are already processed.
        """
        prefix = f"{gender}/images/"
        print(f"Scanning S3 bucket '{S3_BUCKET_NAME}' at prefix '{prefix}' for existing files...")
        existing_prompts = set()
        
        try:
            async with self.session.client("s3", region_name=S3_REGION) as s3:
                paginator = s3.get_paginator("list_objects_v2")
                
                async for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix):
                    if "Contents" not in page:
                        continue
                        
                    for obj in page["Contents"]:
                        # Key: gender/images/1.png
                        key = obj["Key"]
                        # Filename: 1.png
                        filename = os.path.basename(key)
                        # Stem: 1
                        stem, _ = os.path.splitext(filename)
                        
                        if stem.isdigit():
                            existing_prompts.add(stem)
                                
        except Exception as e:
            print(f"Warning: Could not list S3 objects for {gender} (starting fresh?): {e}")
            
        print(f"Found {len(existing_prompts)} existing prompts for {gender} in S3.")
        return existing_prompts

    async def fetch_prompts_from_s3(self, prefix: str = "dataset/prompts/") -> list:
        """
        Fetch prompt text files from S3 and return a list of dictionaries 
        compatible with the main pipeline.
        Expected structure: dataset/prompts/{filename}.txt
        Filename format assumed: {gender}_{number}.txt or just {number}.txt (logic to be defined)
        """
        prompts = []
        print(f"Fetching prompts from S3: {S3_BUCKET_NAME}/{prefix}")
        try:
            async with self.session.client("s3", region_name=S3_REGION) as s3:
                paginator = s3.get_paginator("list_objects_v2")
                async for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix):
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            key = obj["Key"]
                            if not key.endswith(".txt"):
                                continue
                            
                            # Download text
                            response = await s3.get_object(Bucket=S3_BUCKET_NAME, Key=key)
                            text_data = await response['Body'].read()
                            prompt_text = text_data.decode('utf-8').strip()
                            
                            # Parse metadata from content or filename?
                            # Assuming content has headers like "Gender: female" is safer if available,
                            # otherwise inferred from filename or folder.
                            # For now, simplistic parsing or regex could be used if headers exist,
                            # but let's assume raw text and filename inference for basic attributes.
                            
                            filename = os.path.basename(key)
                            stem = os.path.splitext(filename)[0]
                            
                            # Heuristic: female_1.txt -> gender=female, number=1
                            gender = "unknown"
                            prompt_number = stem
                            
                            if "female" in filename.lower():
                                gender = "female"
                            elif "male" in filename.lower():
                                gender = "male"
                                
                            # If content has metadata headers (YAML/Key-Value)
                            dress_name = "N/A"
                            setting = "N/A"
                            
                            # Simple parsing if format matches:
                            # Gender: ...
                            # Dress Name: ...
                            
                            lines = prompt_text.split('\n')
                            final_text = []
                            for line in lines:
                                if ":" in line and len(line.split(":")[0]) < 20: # Key-value candidate
                                    k, v = line.split(":", 1)
                                    k = k.strip().lower()
                                    v = v.strip()
                                    if k == "gender": gender = v.lower()
                                    elif k == "prompt number": prompt_number = v
                                    elif k == "dress name": dress_name = v
                                    elif k == "setting": setting = v
                                else:
                                    final_text.append(line)
                            
                            # Reassemble prompt text (removing consumed headers)
                            clean_prompt = "\n".join(final_text).strip()
                            
                            prompts.append({
                                "prompt_number": prompt_number,
                                "prompt": clean_prompt if clean_prompt else prompt_text, # Fallback
                                "gender": gender,
                                "dress_name": dress_name,
                                "setting": setting,
                                "s3_key": key
                            })
                            
        except Exception as e:
             print(f"Error fetching prompts from S3: {e}")
             
        print(f"Loaded {len(prompts)} prompts from S3.")
        return prompts
