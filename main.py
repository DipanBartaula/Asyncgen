import argparse
import asyncio
import os
from src.parser import parse_prompts
from src.generator import ImageGenerator
from src.s3_uploader import AsyncUploader
from src.config import S3_PREFIX

async def main(model_type="4b", target_gender="all"):
    # 1. Setup
    # Define files by gender
    male_files = ["prompts_male1_reindexed.jsonl", "prompts_male_reindexed.jsonl"]
    female_files = ["prompts_female1_reindexed.jsonl", "prompts_female_reindexed.jsonl"]
    
    jsonl_files = []
    if target_gender == "all" or target_gender == "male":
        jsonl_files.extend(male_files)
    if target_gender == "all" or target_gender == "female":
        jsonl_files.extend(female_files)
        
    print(f"Targeting Gender(s): {target_gender.upper()}")
    print(f"Processing {len(jsonl_files)} files: {jsonl_files}")
    
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
    
    # 2. Processing Loop
    print("Starting generation loop...")
    
    for prompt_data in parse_prompts(jsonl_files):
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

        # Save Locally
        # Structure: output/{gender}/images/{number}.png and output/{gender}/prompts/{number}.txt
        from src.config import OUTPUT_BASE_DIR
        local_gender_dir = OUTPUT_BASE_DIR / gender
        local_images_dir = local_gender_dir / "images"
        local_prompts_dir = local_gender_dir / "prompts"
        
        local_images_dir.mkdir(parents=True, exist_ok=True)
        local_prompts_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Local Image
        local_image_path = local_images_dir / f"{prompt_number}.png"
        image.save(local_image_path)
        
        # Save Local Text
        local_text_path = local_prompts_dir / f"{prompt_number}.txt"
        with open(local_text_path, "w", encoding="utf-8") as f:
            f.write(text_content)
            
        print(f"✓ Saved locally to {local_gender_dir}")

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
