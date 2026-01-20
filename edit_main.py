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
    difficulty = info["difficulty"]
    gender = info["gender"]
    image_id = info["image_id"]
    stem = info["stem"]
    
    # Mirroring Input Path Structure
    # Input Key: dataset/edit_prompts/easy/edit_female/partition_0/1_0.txt
    # We want:   edited_images/easy/edit_female/partition_0/1_0.png
    
    # 1. Get relative path from the prefix
    # key is full s3 key. EDIT_PROMPTS_PREFIX is "dataset/edit_prompts/"
    if s3_key.startswith(EDIT_PROMPTS_PREFIX):
        # relative: easy/edit_female/partition_0/1_0.txt
        relative_path_txt = s3_key[len(EDIT_PROMPTS_PREFIX):]
        # remove extension .txt -> .png
        relative_path_png = os.path.splitext(relative_path_txt)[0] + ".png"
        
        # Construct Target
        target_key = f"{OUTPUT_BASE}{relative_path_png}"
    else:
        # Fallback if something is weird (shouldn't happen given parse logic)
        target_key = f"{OUTPUT_BASE}{difficulty}/{gender}/{stem}.png"
    
    # 1. Define Paths (Source Image)
    if gender == "female":
        source_img_key = f"{SOURCE_IMAGES_BASE_FEMALE}{image_id}.png"
    else:
        source_img_key = f"{SOURCE_IMAGES_BASE_MALE}{image_id}.png"
            
    # 2. Check if exists (Resume)
    if await uploader.check_exists(target_key):
        print(f"Skipping {target_key} (Already exists)")
        return

    # 3. Download Inputs (IO Bound - Parallelize)
    print(f"[{stem}] Downloading source image: {source_img_key}")
    source_image = await uploader.download_image(source_img_key)
    if source_image is None:
        print(f"[{stem}] SKIPPING: Source image not found ({source_img_key})")
        return
        
    print(f"[{stem}] Downloading prompt text: {s3_key}")
    prompt_text = await uploader.download_text(s3_key)
    if not prompt_text:
            print(f"[{stem}] SKIPPING: Prompt text is empty or missing")
            return
    
    # 4. Generate (GPU Bound - Serialized)
    print(f"[{stem}] Waiting for GPU slot...")
    async with semaphore:
        print(f"[{stem}] GPU SLOT ACQUIRED. Starting generation...")
        try:
            result_image = await asyncio.to_thread(
                generator.generate,
                prompt=prompt_text,
                image=source_image,
                strength=0.75, # Default strength for editing
                width=source_image.width, 
                height=source_image.height
            )
            print(f"[{stem}] Generation COMPLETED successfully.")
        except Exception as e:
            print(f"[{stem}] FAILURE during generation: {e}")
            return

    # 5. Upload (IO Bound - Parallelize)
    print(f"[{stem}] Uploading result to: {target_key}")
    await uploader.upload_edited_image(result_image, target_key)
    print(f"[{stem}] DONE. Process finished.")

async def main(model_type="9b", difficulty_target=None, partition_target=None, gender_target=None):
    print(f"Initializing Edit Pipeline with Model: {model_type}")
    print(f"Targeting Difficulty: {difficulty_target if difficulty_target else 'ALL'}")
    print(f"Targeting Gender: {gender_target if gender_target else 'ALL'}")
    print(f"Targeting Partition: {partition_target if partition_target else 'ALL'}")
    
    # Init Generator
    generator = ImageGenerator(model_type=model_type)
    generator.load_model()
    
    # Init Uploader
    uploader = AsyncUploader()
    
    # List Prompts
    scan_prefix = EDIT_PROMPTS_PREFIX
    if difficulty_target:
        scan_prefix = f"{EDIT_PROMPTS_PREFIX}{difficulty_target}/"
        # Optional: If we have gender, AND difficulty, we could narrow down prefix further:
        # scan_prefix = ".../easy/edit_female/"
        if gender_target:
             # Map 'female' -> 'edit_female', 'male' -> 'edit_male'
             gender_dir = f"edit_{gender_target}"
             scan_prefix = f"{scan_prefix}{gender_dir}/"
    
    print(f"Scanning prompts in {S3_BUCKET_NAME}/{scan_prefix}...")
    
    tasks = []

    # We use a separate boto3 client for the initial listing to build the queue
    import boto3
    s3_client = boto3.client(
        "s3", 
        region_name=S3_REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
    )
    
    paginator = s3_client.get_paginator("list_objects_v2")
    
    # Limit concurrency
    semaphore = asyncio.Semaphore(1) 
    
    prompt_files = []
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=scan_prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                if key.endswith(".txt"):
                    # Check Partition Filter
                    if partition_target:
                        parts = key.split('/')
                        # Robust check: Check if the specific partition folder exists in the path
                        # dataset/edit_prompts/easy/edit_female/partition_0/image.txt
                        if partition_target in parts:
                             pass # Match
                        else:
                             continue
                    
                    # Check Gender Filter (Explicit check just in case prefix didn't cover it or mixed usage)
                    if gender_target:
                        # Expect 'edit_female' or 'edit_male' in path
                         if f"edit_{gender_target}" not in key:
                             continue

                    prompt_files.append(key)
                    
    print(f"Found {len(prompt_files)} matching prompt files. Queuing...")

    total_tasks = 0
    for key in prompt_files:
        info = parse_s3_key_info(key)
        if info:
            if difficulty_target and info["difficulty"] != difficulty_target:
                continue
            if gender_target and info["gender"] != gender_target:
                continue
                
            tasks.append(process_prompt(generator, uploader, key, info, semaphore))
            total_tasks += 1
            
    print(f"Queued {total_tasks} tasks. Starting execution...")
    
    if tasks:
        await asyncio.gather(*tasks)
    
    print("All edit tasks completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="9b", help="Model type (default: 9b)")
    parser.add_argument("--difficulty", type=str, default=None, choices=["easy", "medium", "hard"], help="Filter by difficulty (easy/medium/hard)")
    parser.add_argument("--partition", type=str, default=None, help="Filter by partition folder name (e.g., partition_0)")
    parser.add_argument("--gender", type=str, default=None, choices=["male", "female"], help="Filter by gender (male/female)")
    
    args = parser.parse_args()
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
        
    asyncio.run(main(model_type=args.model, difficulty_target=args.difficulty, partition_target=args.partition, gender_target=args.gender))
