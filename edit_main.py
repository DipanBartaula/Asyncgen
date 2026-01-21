import asyncio
import os
import argparse
import boto3
from src.generator import ImageGenerator
from src.s3_uploader import AsyncUploader
from src.config import S3_BUCKET_NAME, S3_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

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
    
    if len(parts) < 3:
        return None
        
    difficulty = parts[0] # easy, medium, hard
    gender_dir = parts[1] # edit_female, edit_male
    
    # Try to identify partition folder
    # It usually comes after gender_dir and before filename
    # parts: ['easy', 'edit_female', 'partition_0', '1044_3_edit.txt']
    # If standard structure: parts[-2] is usually partition
    partition_name = "unknown_partition"
    if len(parts) >= 3:
        # Check if the folder before filename starts with 'partition'
        possible_part = parts[-2]
        if "partition" in possible_part:
            partition_name = possible_part
            
    filename = parts[-1]
    
    if not filename.endswith(".txt"):
        return None
        
    stem = os.path.splitext(filename)[0]
    
    # Expect stem: "1044_3_edit" -> image_id "1044"
    # Logic: The first part before the first underscore is the ID.
    if "_" not in stem:
        image_id = stem
        epoch = "0"
        remainder = "edit"
    else:
        # Split on underscores
        # "1044_3_edit" -> ['1044', '3', 'edit']
        subparts = stem.split('_')
        image_id = subparts[0]
        # epoch logic is less critical but we can store the rest
        # We need the '3_edit' part
        remainder = "_".join(subparts[1:])
        
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
        "partition": partition_name,
        "remainder": remainder,
        "stem": stem
    }

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
    
    # ---------------------------------------------------------
    # OPTIMIZATION: SCAN EXISTING OUTPUTS FIRST (RESUME LOGIC)
    # ---------------------------------------------------------
    # We want to avoid calling uploader.check_exists() N times.
    # Instead, we list the output directory once and filter locally.
    
    existing_outputs = set()
    s3_client = boto3.client(
        "s3", 
        region_name=S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # Determine where to scan for outputs.
    # Output structure: edited_images/{difficulty}/{gender}/
    # If difficulty and gender are known, we scan that specific folder.
    # If not, we scan the root edited_images/ recursively (could be slower but necessary).
    
    output_scan_prefixes = []
    
    if difficulty_target and gender_target:
        # Specific scan: edited_images/easy/female/
        output_scan_prefixes.append(f"{OUTPUT_BASE}{difficulty_target}/{gender_target}/")
        
    elif difficulty_target:
        # Scan all genders for this difficulty: edited_images/easy/
        output_scan_prefixes.append(f"{OUTPUT_BASE}{difficulty_target}/")
        
    elif gender_target:
        # Scan all difficulties for this gender? Structure is diff/gender.
        # We would have to scan: easy/gender/, medium/gender/, hard/gender/
        for diff in ["easy", "medium", "hard"]:
             output_scan_prefixes.append(f"{OUTPUT_BASE}{diff}/{gender_target}/")
    else:
        # Scan everything
        output_scan_prefixes.append(OUTPUT_BASE)
        
    print(f"Checking existing outputs for resume capability in: {output_scan_prefixes}")
    
    output_paginator = s3_client.get_paginator("list_objects_v2")
    
    for prefix in output_scan_prefixes:
        for page in output_paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    # Key: edited_images/easy/female/1044_partition_0_3_edit.png
                    # We store the full key in the set for exact matching
                    existing_outputs.add(obj["Key"])
                    
    print(f"Found {len(existing_outputs)} existing edited images.")

    # ---------------------------------------------------------
    # SCAN PROMPTS
    # ---------------------------------------------------------
    
    # List Prompts
    scan_prefix = EDIT_PROMPTS_PREFIX
    if difficulty_target:
        scan_prefix = f"{EDIT_PROMPTS_PREFIX}{difficulty_target}/"
        if gender_target:
             # Map 'female' -> 'edit_female', 'male' -> 'edit_male'
             gender_dir = f"edit_{gender_target}"
             scan_prefix = f"{scan_prefix}{gender_dir}/"
    
    print(f"Scanning prompts in {S3_BUCKET_NAME}/{scan_prefix}...")
    
    tasks = []
    
    # We use the same s3_client for paginator
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
                        if partition_target in parts:
                             pass # Match
                        else:
                             continue
                    
                    if gender_target:
                         if f"edit_{gender_target}" not in key:
                             continue

                    prompt_files.append(key)
                    
    print(f"Found {len(prompt_files)} matching prompt files.")
    
    total_tasks = 0
    skipped_count = 0
    
    for key in prompt_files:
        info = parse_s3_key_info(key)
        if info:
            if difficulty_target and info["difficulty"] != difficulty_target:
                continue
            if gender_target and info["gender"] != gender_target:
                continue
            
            # Construct Target Key
            # Logic: {image_id}_{partition}_{remainder}.png
            part = info.get("partition", "unknown")
            rem = info.get("remainder", "")
            img_id = info["image_id"]
            diff = info["difficulty"]
            gen = info["gender"]
            
            new_filename_stem = f"{img_id}_{part}_{rem}"
            target_key = f"{OUTPUT_BASE}{diff}/{gen}/{new_filename_stem}.png"
            
            # CHECK IF EXISTS (Resume Logic)
            if target_key in existing_outputs:
                skipped_count += 1
                continue
                
            tasks.append(process_prompt(generator, uploader, key, target_key, info, semaphore))
            total_tasks += 1
            
    print(f"Queued {total_tasks} tasks. Skipped {skipped_count} already processed.")
    print("Starting execution...")
    
    if tasks:
        await asyncio.gather(*tasks)
    
    print("All edit tasks completed.")

async def process_prompt(generator, uploader, s3_key, target_key, info, semaphore):
    # s3_key: Source Prompt S3 Key
    # target_key: Destination Image S3 Key
    
    stem = info["stem"]
    image_id = info["image_id"]
    gender = info["gender"]
    
    # 1. Define Source Image Path
    if gender == "female":
        source_img_key = f"{SOURCE_IMAGES_BASE_FEMALE}{image_id}.png"
    else:
        source_img_key = f"{SOURCE_IMAGES_BASE_MALE}{image_id}.png"
        
    # Note: We already checked existence in the main loop, so we skip check_exists here
    # to save time, unless paranoid about race conditions (unlikely in this batch job).

    # 2. Download Inputs (IO Bound)
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
    
    # 3. Generate (GPU Bound)
    print(f"[{stem}] Waiting for GPU slot...")
    async with semaphore:
        print(f"[{stem}] GPU SLOT ACQUIRED. Starting generation...")
        try:
            result_image = await asyncio.to_thread(
                generator.generate,
                prompt=prompt_text,
                image=source_image,
                strength=0.75, 
                width=source_image.width, 
                height=source_image.height
            )
            print(f"[{stem}] Generation COMPLETED successfully.")
        except Exception as e:
            print(f"[{stem}] FAILURE during generation: {e}")
            return

    # 4. Upload (IO Bound)
    print(f"[{stem}] Uploading result to: {target_key}")
    await uploader.upload_edited_image(result_image, target_key)
    print(f"[{stem}] DONE.")

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
