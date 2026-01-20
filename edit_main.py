import asyncio
import os
import argparse
from src.generator import ImageGenerator
from src.s3_uploader import AsyncUploader
from src.config import S3_BUCKET_NAME, S3_REGION

# Constants
EDIT_PROMPTS_PREFIX = "dataset/edit_prompts/"
SOURCE_IMAGES_BASE_FEMALE = "dataset/female/female/images/"
SOURCE_IMAGES_BASE_MALE = "dataset/male/male/images/"
OUTPUT_BASE = "edited_images/"

def parse_s3_key_info(key):
    """
    Parses the S3 key for an edit prompt txt file.
    Expected format: dataset/edit_prompts/{difficulty}/{gender_dir}/{partition}/.../{filename}.txt
    Returns: difficulty, gender, result_gender, image_id, epoch, filename_stem
    """
    # Remove prefix
    if not key.startswith(EDIT_PROMPTS_PREFIX):
        return None
    
    rel_path = key[len(EDIT_PROMPTS_PREFIX):]
    parts = rel_path.split('/')
    
    # We need at least difficulty, gender_dir, and filename
    # Structure: easy/edit_female/partition_0/1_0.txt  (4 parts)
    # Structure: easy/edit_female/1_0.txt (3 parts - if partition is missing)
    
    if len(parts) < 3:
        return None
        
    difficulty = parts[0] # easy, medium, hard
    gender_dir = parts[1] # edit_female, edit_male
    filename = parts[-1]
    
    if not filename.endswith(".txt"):
        return None
        
    stem = os.path.splitext(filename)[0]
    
    # Expect stem: "1_0" -> image_id "1", epoch "0"
    if "_" not in stem:
        # Fallback if specific format not followed
        image_id = stem
        epoch = "0"
    else:
        # Split on first underscore? or last? User said "1_0", let's assume {id}_{epoch}
        # Image IDs can be large numbers. Epoch is likely small.
        # But wait, image filenames are 1.png. 
        # If stem is 1_0, split('_') gives ['1', '0'].
        subparts = stem.split('_')
        image_id = subparts[0]
        epoch = "_".join(subparts[1:]) # Rest is epoch
        
    # Map gender
    if "female" in gender_dir:
        result_gender = "female"
    elif "male" in gender_dir:
        result_gender = "male"
    else:
        return None
        
    return {
        "difficulty": difficulty,
        "gender": result_gender, 
        "image_id": image_id,
        "epoch": epoch,
        "stem": stem
    }

async def process_prompt(generator, uploader, s3_key, info, semaphore):
    async with semaphore:
        difficulty = info["difficulty"]
        gender = info["gender"]
        image_id = info["image_id"]
        stem = info["stem"]
        
        # 1. Define Paths
        # Source Image
        if gender == "female":
            source_img_key = f"{SOURCE_IMAGES_BASE_FEMALE}{image_id}.png"
        else:
            source_img_key = f"{SOURCE_IMAGES_BASE_MALE}{image_id}.png"
            
        # Target Output
        # edited_images/{difficulty}/{gender}/{stem}.png
        target_key = f"{OUTPUT_BASE}{difficulty}/{gender}/{stem}.png"
        
        # 2. Check if exists (Resume)
        if await uploader.check_exists(target_key):
            print(f"Skipping {target_key} (Already exists)")
            return

        print(f"Processing: Prompt={s3_key} -> Img={source_img_key} -> Out={target_key}")

        # 3. Download Source Image
        source_image = await uploader.download_image(source_img_key)
        if source_image is None:
            print(f"Skipping {stem}: Source image not found ({source_img_key})")
            return
            
        # 4. Download Prompt Text
        prompt_text = await uploader.download_text(s3_key)
        if not prompt_text:
             print(f"Skipping {stem}: Prompt text is empty or missing")
             return
        
        # 5. Generate (Edit)
        # Run synchronous generation in thread
        print(f"Generating {stem}...")
        try:
            result_image = await asyncio.to_thread(
                generator.generate,
                prompt=prompt_text,
                image=source_image,
                strength=0.75, # Default strength for editing
                width=source_image.width, # Maintain aspect/size best as possible or fixed?
                height=source_image.height
            )
        except Exception as e:
            print(f"Generation failed for {stem}: {e}")
            return

        # 6. Upload
        await uploader.upload_edited_image(result_image, target_key)

async def main(model_type="9b", partition_filter=None):
    print(f"Initializing Edit Pipeline with Model: {model_type}")
    
    # Init Generator
    generator = ImageGenerator(model_type=model_type)
    generator.load_model()
    
    # Init Uploader
    uploader = AsyncUploader()
    
    # List Prompts
    print(f"Scanning prompts in {S3_BUCKET_NAME}/{EDIT_PROMPTS_PREFIX}...")
    
    tasks = []
    
    # We use basic boto3 for listing to be simple or reuse uploader session?
    # uploader has a session but it's async context manager based usually.
    # Let's verify uploader implementation. 'self.session = aioboto3.Session(...)'.
    
    # We can use a separate boto3 client for the initial listing to build the queue
    import boto3
    s3_client = boto3.client(
        "s3", 
        region_name=S3_REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
    )
    
    paginator = s3_client.get_paginator("list_objects_v2")
    
    # Limit concurrency
    semaphore = asyncio.Semaphore(1) # Processing one at a time per GPU really
    
    prompt_files = []
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=EDIT_PROMPTS_PREFIX):
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                if key.endswith(".txt"):
                    prompt_files.append(key)
                    
    print(f"Found {len(prompt_files)} prompt files. Filtering and queuing...")

    total_tasks = 0
    for key in prompt_files:
        info = parse_s3_key_info(key)
        if info:
            # Create task
            tasks.append(process_prompt(generator, uploader, key, info, semaphore))
            total_tasks += 1
            
    print(f"Queued {total_tasks} tasks. Starting execution...")
    
    if tasks:
        await asyncio.gather(*tasks)
    
    print("All edit tasks completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="9b", help="Model type (default: 9b)")
    args = parser.parse_args()
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
        
    asyncio.run(main(model_type=args.model))
