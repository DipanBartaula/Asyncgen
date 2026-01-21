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

import random

async def download_worker(uploader, prompt_files, existing_outputs, queue, generator_model_type):
    """
    Producer: Downloads images and prompts, puts them in the queue.
    """
    print(f"Producer started. Processing {len(prompt_files)} files...")
    random.shuffle(prompt_files) # Randomize order as requested
    
    skipped = 0
    queued = 0
    
    for key in prompt_files:
        info = parse_s3_key_info(key)
        if not info: 
            continue
            
        # Construct Target Key
        part = info.get("partition", "unknown")
        rem = info.get("remainder", "")
        img_id = info["image_id"]
        diff = info["difficulty"]
        gen = info["gender"]
        
        new_filename_stem = f"{img_id}_{part}_{rem}"
        target_key = f"{OUTPUT_BASE}{diff}/{gen}/{new_filename_stem}.png"
        
        # Resume Logic
        if target_key in existing_outputs:
            skipped += 1
            continue
            
        # Check Gender/Source Path
        if gen == "female":
            source_img_key = f"{SOURCE_IMAGES_BASE_FEMALE}{img_id}.png"
        else:
            source_img_key = f"{SOURCE_IMAGES_BASE_MALE}{img_id}.png"
            
        stem = info["stem"]
        print(f"[{stem}] Downloading inputs...")
        
        # Parallel Download of Image and Text
        img_task = asyncio.create_task(uploader.download_image(source_img_key))
        txt_task = asyncio.create_task(uploader.download_text(key))
        
        source_image, prompt_text = await asyncio.gather(img_task, txt_task)
        
        if source_image is None or not prompt_text:
            print(f"[{stem}] SKIP: Missing input files.")
            continue
            
        # Put into Queue (Blocks if full, creating backpressure)
        # Item: (stem, prompt_text, source_image, target_key)
        await queue.put((stem, prompt_text, source_image, target_key))
        queued += 1
        
    print(f"Producer finished. Queued: {queued}, Skipped: {skipped}")
    await queue.put(None) # Sentinel to signal end

async def gpu_worker(generator, uploader, queue, semaphore):
    """
    Consumer: Takes ready data from queue, runs GPU generation, starts background upload.
    """
    print("GPU Worker started. Waiting for data...")
    upload_tasks = set()
    
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
            
        stem, prompt_text, source_image, target_key = item
        
        # GPU Generation
        print(f"[{stem}] Processing on GPU...")
        try:
            # We don't strictly need semaphore if only 1 consumer exists, 
            # but good for safety if we scale consumer count.
            async with semaphore: 
                result_image = await asyncio.to_thread(
                    generator.generate,
                    prompt=prompt_text,
                    image=source_image,
                    strength=0.75,
                    width=source_image.width, 
                    height=source_image.height
                )
        except Exception as e:
            print(f"[{stem}] GENERATION FAILED: {e}")
            queue.task_done()
            continue
            
        # Fire and Forget Upload (Background)
        print(f"[{stem}] Generation done. Queuing upload...")
        
        # Define wrapper to handle upload and cleanup set
        task = asyncio.create_task(upload_wrapper(uploader, result_image, target_key, stem))
        upload_tasks.add(task)
        task.add_done_callback(upload_tasks.discard)
        
        queue.task_done()
        
    # Wait for remaining uploads
    if upload_tasks:
        print(f"Waiting for {len(upload_tasks)} pending uploads...")
        await asyncio.gather(*upload_tasks)
        
    print("GPU Worker finished.")

async def upload_wrapper(uploader, image, key, stem):
    try:
        await uploader.upload_edited_image(image, key)
        print(f"[{stem}] ✓ Upload Complete.")
    except Exception as e:
        print(f"[{stem}] x Upload Failed: {e}")

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
    
    # 1. Scan Existing Outputs (Resume)
    existing_outputs = set()
    s3_client = boto3.client(
        "s3", 
        region_name=S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    output_scan_prefixes = []
    if difficulty_target and gender_target:
        output_scan_prefixes.append(f"{OUTPUT_BASE}{difficulty_target}/{gender_target}/")
    elif difficulty_target:
        output_scan_prefixes.append(f"{OUTPUT_BASE}{difficulty_target}/")
    elif gender_target:
        for diff in ["easy", "medium", "hard"]:
             output_scan_prefixes.append(f"{OUTPUT_BASE}{diff}/{gender_target}/")
    else:
        output_scan_prefixes.append(OUTPUT_BASE)
        
    print(f"Checking existing outputs for resume capability...")
    output_paginator = s3_client.get_paginator("list_objects_v2")
    for prefix in output_scan_prefixes:
        for page in output_paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix):
            if "Contents" in page:
                for obj in page["Contents"]:
                    existing_outputs.add(obj["Key"])
    print(f"Found {len(existing_outputs)} existing edited images.")

    # 2. Scan Inputs
    scan_prefix = EDIT_PROMPTS_PREFIX
    if difficulty_target:
        scan_prefix = f"{EDIT_PROMPTS_PREFIX}{difficulty_target}/"
        if gender_target:
             gender_dir = f"edit_{gender_target}"
             scan_prefix = f"{scan_prefix}{gender_dir}/"
             if partition_target:
                 scan_prefix = f"{scan_prefix}{partition_target}/"
    
    print(f"Scanning prompts inputs in {scan_prefix}...")
    prompt_files = []
    paginator = s3_client.get_paginator("list_objects_v2")
    
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=scan_prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                if key.endswith(".txt"):
                    # Double check filters locally just in case
                    if partition_target and partition_target not in key: continue
                    if gender_target and f"edit_{gender_target}" not in key: continue
                    prompt_files.append(key)
                    
    print(f"Found {len(prompt_files)} matching input files.")
    
    # 3. Queue & Tasks
    # Maxsize limits memory usage. 
    # e.g., keep 10 images ready in RAM.
    queue = asyncio.Queue(maxsize=10) 
    
    # Limit Concurrency
    semaphore = asyncio.Semaphore(1)
    
    # Start Producer
    producer_task = asyncio.create_task(download_worker(uploader, prompt_files, existing_outputs, queue, model_type))
    
    # Start Consumer (GPU)
    consumer_task = asyncio.create_task(gpu_worker(generator, uploader, queue, semaphore))
    
    print("Pipeline started. Press Ctrl+C to stop.")
    
    await asyncio.gather(producer_task, consumer_task)
    
    print("All tasks finished.")

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
