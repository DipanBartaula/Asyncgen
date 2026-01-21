import asyncio
import os
import argparse
import boto3
import random
import json
from io import BytesIO
from src.generator import ImageGenerator
from src.s3_uploader import AsyncUploader
from src.config import S3_BUCKET_NAME, S3_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

# Constants
EDITED_IMAGES_BASE = "edited_images/"
CLOTHES_BASE = "dataset/clothes/"
OUTPUT_ULTIMATE_BASE = "dataset_ultimate/"

# Prompt for VTON
VTON_PROMPT = "A person wearing this cloth" 

def parse_s3_key_info(key):
    # Parses edited_images/{difficulty}/{gender}/{filename}
    # Filename format: {image_id}_{partition}_{remainder}.png
    
    parts = key.split('/')
    if len(parts) < 3: return None
    
    # parts: ['edited_images', 'easy', 'female', '1044_partition_0_3_edit.png']
    difficulty = parts[1]
    gender = parts[2]
    filename = parts[-1]
    
    if not filename.endswith(".png"): return None
    
    stem = os.path.splitext(filename)[0]
    
    # Extract partition using simple split if valid format
    # 1044_partition_0_3_edit
    
    partition_name = "unknown"
    if "partition_" in stem:
        # crude extraction
        subparts = stem.split('_')
        for i, p in enumerate(subparts):
            if p == "partition" and i+1 < len(subparts):
                partition_name = f"partition_{subparts[i+1]}"
                break
                
    return {
        "difficulty": difficulty,
        "gender": gender,
        "filename": filename,
        "stem": stem,
        "partition": partition_name
    }

async def get_clothes_list(s3_client, gender):
    # List all clothes for the gender
    # Structure: dataset/clothes/{gender}/images/{filename}.png
    prefix = f"{CLOTHES_BASE}{gender}/images/"
    clothes = []
    print(f"Listing clothes from {prefix}...")
    
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                if key.endswith(('.png', '.jpg', '.jpeg')):
                    clothes.append(key)
    print(f"Found {len(clothes)} clothes for {gender}.")
    return clothes

async def download_worker(uploader, person_files, clothes_list, queue):
    """
    Producer: Downloads person + random cloth + cloth prompt -> Queue
    """
    print(f"Producer started. Processing {len(person_files)} person images...")
    
    # Sequential Processing
    person_files.sort() 
    
    for person_key in person_files:
        if not clothes_list:
            print("Error: No clothes available!")
            break
            
        # Pick Random Cloth
        cloth_key = random.choice(clothes_list)
        
        # Construct Cloth Prompt Key
        # dataset/clothes/female/images/1.png -> dataset/clothes/female/prompts/1.txt
        prompt_key = cloth_key.replace("/images/", "/prompts/")
        prompt_key = os.path.splitext(prompt_key)[0] + ".txt"
        
        info = parse_s3_key_info(person_key)
        stem = info["stem"]
        diff = info["difficulty"]
        gen = info["gender"]
        
        print(f"[{stem}] Downloading Person: {person_key} + Cloth: {cloth_key}")
        
        # Parallel Download: Person Img, Cloth Img, Cloth Prompt
        p_task = asyncio.create_task(uploader.download_image(person_key))
        c_task = asyncio.create_task(uploader.download_image(cloth_key))
        txt_task = asyncio.create_task(uploader.download_text(prompt_key))
        
        person_img, cloth_img, prompt_text = await asyncio.gather(p_task, c_task, txt_task)
        
        if person_img is None or cloth_img is None:
            print(f"[{stem}] SKIP: Input missing.")
            continue
            
        if not prompt_text:
            print(f"[{stem}] Warning: Cloth prompt missing ({prompt_key}). Using default.")
            prompt_text = VTON_PROMPT
            
        await queue.put((info, person_img, cloth_img, prompt_text, person_key, cloth_key))
        
    await queue.put(None)

async def gpu_worker(generator, uploader, queue, semaphore, jsonl_buffer):
    """
    Consumer: Generates VTON -> Queues Upload -> Updates JSONL
    """
    print("GPU Worker started.")
    upload_tasks = set()
    
    while True:
        item = await queue.get()
        if item is None:
            queue.task_done()
            break
            
        info, person_img, cloth_img, prompt_text, person_key_s3, cloth_key_s3 = item
        stem = info["stem"]
        diff = info["difficulty"]
        gen = info["gender"]
        
        print(f"[{stem}] Generating VTON with prompt: {prompt_text[:30]}...")
        try:
            async with semaphore:
                result_image = await asyncio.to_thread(
                    generator.generate,
                    prompt=prompt_text,     # Uses specific cloth prompt
                    image=person_img,       # Person
                    cloth_image=cloth_img,  # Cloth (passed as 2nd arg to pipeline)
                    width=person_img.width,
                    height=person_img.height,
                    steps=20 
                )
        except Exception as e:
            print(f"[{stem}] Generation FAILED: {e}")
            queue.task_done()
            continue
            
        # Uploads
        # Structure: dataset_ultimate/{diff}/{gen}/{type}/{filename}
        
        # 1. Try-On Result
        try_on_name = f"{stem}_vton.png"
        try_on_key = f"{OUTPUT_ULTIMATE_BASE}{diff}/{gen}/try_on_image/{try_on_name}"
        
        # 2. Initial Person Copy
        # We re-upload the PIL image we downloaded. 
        # Alternatively we could S3 Copy, but re-uploading ensures consistent naming.
        person_name = f"{stem}_person.png"
        initial_key = f"{OUTPUT_ULTIMATE_BASE}{diff}/{gen}/initial_image/{person_name}"
        
        # 3. Cloth Copy
        cloth_filename = os.path.basename(cloth_key_s3)
        # Make cloth filename unique potentially? Or keep original. 
        # User said "proper naming convention". I'll prepend stem to match pair? 
        # "saved using proper naming convention". 
        # Let's clean it: {stem}_cloth_{original_name}
        cloth_final_name = f"{stem}_cloth_{cloth_filename}"
        cloth_key = f"{OUTPUT_ULTIMATE_BASE}{diff}/{gen}/cloth_image/{cloth_final_name}"
        
        print(f"[{stem}] Uploading triplet...")
        
        t1 = asyncio.create_task(uploader.upload_edited_image(result_image, try_on_key))
        t2 = asyncio.create_task(uploader.upload_edited_image(person_img, initial_key))
        t3 = asyncio.create_task(uploader.upload_edited_image(cloth_img, cloth_key))
        
        # Add to set to await later if needed, or simple await now?
        # Await now ensures we don't spam S3 too hard/OOM, but parallel is better.
        # Let's fire and forget but track
        for t in [t1, t2, t3]:
            upload_tasks.add(t)
            t.add_done_callback(upload_tasks.discard)
            
        # Add to JSONL Buffer
        # { "src": initial_key, "cloth": cloth_key, "tgt": try_on_key }
        jsonl_buffer.append({
            "initial_image": f"s3://{S3_BUCKET_NAME}/{initial_key}",
            "cloth_image": f"s3://{S3_BUCKET_NAME}/{cloth_key}",
            "try_on_image": f"s3://{S3_BUCKET_NAME}/{try_on_key}"
        })
        
        queue.task_done()
        
    if upload_tasks:
        print(f"Waiting for {len(upload_tasks)} uploads...")
        await asyncio.gather(*upload_tasks)

async def main(model_type="9b", difficulty_target=None, partition_target=None, gender_target=None):
    print("Initializing VTON Pipeline...")
    
    generator = ImageGenerator(model_type=model_type)
    generator.load_model()
    
    uploader = AsyncUploader()
    
    s3_client = boto3.client(
        "s3", 
        region_name=S3_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    # 1. Get Clothes List (Gender Specific)
    clothes_list = []
    if gender_target:
        clothes_list = await get_clothes_list(s3_client, gender_target)
    else:
        print("Warning: No gender target! Clothes mixing might happen if implemented generally.")
        # For strict VTON, we assume script runs per gender
        return

    # 2. Get Person Images (Input)
    # Search in: edited_images/{difficulty}/{gender}
    # Filter by: partition
    
    scan_prefix = f"{EDITED_IMAGES_BASE}{difficulty_target}/{gender_target}/"
    print(f"Scanning inputs in {scan_prefix}...")
    
    person_files = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=scan_prefix):
        if "Contents" in page:
            for obj in page["Contents"]:
                key = obj["Key"]
                if not key.endswith(".png"): continue
                
                # Check partition
                if partition_target and partition_target not in key:
                    continue
                    
                person_files.append(key)
                
    print(f"Found {len(person_files)} person images for VTON.")
    
    # 3. Pipeline
    queue = asyncio.Queue(maxsize=10)
    jsonl_buffer = []
    semaphore = asyncio.Semaphore(1)
    
    p_task = asyncio.create_task(download_worker(uploader, person_files, clothes_list, queue))
    c_task = asyncio.create_task(gpu_worker(generator, uploader, queue, semaphore, jsonl_buffer))
    
    await asyncio.gather(p_task, c_task)
    
    # 4. Save JSONL
    if jsonl_buffer:
        jsonl_filename = f"{difficulty_target}_{gender_target}_{partition_target}.jsonl"
        jsonl_key = f"{OUTPUT_ULTIMATE_BASE}{jsonl_filename}"
        
        buffer = BytesIO()
        for item in jsonl_buffer:
            line = json.dumps(item) + "\n"
            buffer.write(line.encode('utf-8'))
        buffer.seek(0)
        
        print(f"Uploading JSONL to {jsonl_key}...")
        await s3_client.upload_fileobj(buffer, S3_BUCKET_NAME, jsonl_key)
        print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="9b")
    parser.add_argument("--difficulty", type=str, required=True)
    parser.add_argument("--gender", type=str, required=True)
    parser.add_argument("--partition", type=str, required=True)
    
    args = parser.parse_args()
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass
        
    asyncio.run(main(args.model, args.difficulty, args.partition, args.gender))
