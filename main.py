import argparse
import asyncio
import os
from src.parser import parse_prompts
from src.generator import ImageGenerator
from src.s3_uploader import AsyncUploader
from src.config import S3_PREFIX

async def main(model_type="4b", target_gender="all"):
    # 1. Setup
    print(f"Targeting Gender(s): {target_gender.upper()}")
    
    # Initialize Generator (Sync, Heavy Resource)
    generator = ImageGenerator(model_type=model_type)
    generator.load_model()
    
    # Initialize Uploader
    uploader = AsyncUploader()
    
    # Check S3 for existing prompts to resume (only for relevant genders)
    processed_male = set()
    processed_female = set()
    
    if target_gender in ["all", "male"]:
        processed_male = await uploader.get_existing_prompts("male")
    if target_gender in ["all", "female"]:
        processed_female = await uploader.get_existing_prompts("female")

    upload_tasks = []
    
    # Fetch prompts from S3
    # Assuming prompts are stored in "dataset/prompts/" as per previous context or we can make it configurable
    # If the user has specific folders per gender, we might need to fetch multiple prefixes.
    # For now, let's assume a general "dataset/prompts/" prefix or similar.
    # If the user meant the 'edit_prompts', that's in edit_main.py. 
    # For generation, we likely need a source of truth for prompts. 
    # Since the JSONL files were "prompts_male...jsonl", we assume they are now individual text files in S3.
    
    s3_prompts = []
    # Fetch male prompts if needed
    if target_gender in ["all", "male"]:
         # Assuming structured as dataset/prompts/male/ from previous discussions or just dataset/prompts/
         # Let's try fetching from a probable location. The user didn't strictly specify the S3 source folder for *generation* prompts, 
         # but `edit_main.py` uses `dataset/edit_prompts/`. 
         # Let's assume a strictly defined path `dataset/prompts/`.
         s3_prompts.extend(await uploader.fetch_prompts_from_s3(prefix="dataset/prompts/"))

    # 2. Processing Loop
    print("Starting generation loop...")
    
    for prompt_data in s3_prompts:
        prompt_number = prompt_data.get("prompt_number")
        prompt_text = prompt_data.get("prompt", "")
        dress_name = prompt_data.get("dress_name", "N/A")
        setting = prompt_data.get("setting", "N/A")
        gender = prompt_data.get("gender", "unknown")
        
        # Double check we are processing the right gender (parser handles file path logic, but good to be safe)
        if target_gender != "all" and gender != target_gender:
            continue
            
        print(f"\nProcessing Prompt {prompt_number} ({gender})...")
        
        # Resume Logic
        if gender == "male" and str(prompt_number) in processed_male:
            print(f"Skipping Male Prompt {prompt_number} (Already exists in S3).")
            continue
        if gender == "female" and str(prompt_number) in processed_female:
            print(f"Skipping Female Prompt {prompt_number} (Already exists in S3).")
            continue
        
        # synchronous generation
        try:
            image = await asyncio.to_thread(generator.generate, prompt_text)
        except Exception as e:
            print(f"Failed to generate for prompt {prompt_number}: {e}")
            continue
            
        # Prepare text content
        text_content = f"""Prompt Number: {prompt_number}
Gender: {gender}
Dress Name: {dress_name}
Setting: {setting}

{prompt_text}"""

        # Upload to S3 (Directly from memory)
        print(f"Queueing upload to S3 for {gender}/{prompt_number}...")

        # Fire off async upload (Pass gender to handle paths)
        task = asyncio.create_task(
            uploader.upload_data(image, text_content, gender, str(prompt_number))
        )
        upload_tasks.append(task)
        
        # Clean up finished tasks
        upload_tasks = [t for t in upload_tasks if not t.done()]
        
    
    # 3. Wait for remaining uploads
    if upload_tasks:
        print(f"\nWaiting for {len(upload_tasks)} pending uploads...")
        await asyncio.gather(*upload_tasks)
    
    print("\nAll done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async Image Generation Pipeline")
    parser.add_argument("--model", type=str, default="4b", choices=["nvfp4", "4b", "9b"], help="Model variant to use")
    parser.add_argument("--gender", type=str, default="all", choices=["all", "male", "female"], help="Target gender to process")
    
    args = parser.parse_args()
    
    asyncio.run(main(model_type=args.model, target_gender=args.gender))
