import boto3
import os
from botocore.exceptions import NoCredentialsError, ClientError

# Attempt to load configuration from src if available
try:
    from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_REGION, S3_BUCKET_NAME
except ImportError:
    # Fallback if run standalone without src in path
    from dotenv import load_dotenv
    load_dotenv()
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    S3_REGION = os.getenv("S3_REGION", "ap-south-1")
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "p1-to-ep1")

# Override bucket name as per user request if config imports something else, 
# although user config edit had "cloth", the specific task request context was "p1-to-ep1". 
# However, the user provided config had "cloth". 
# Let's stick to "p1-to-ep1" as per the original "separate.py" request unless user changed mind.
# The user's specific request was: "uses teh aws s3 bucket p1-to-ep1". 
# The config update was just for credentials. I will enforce p1-to-ep1.
BUCKET_NAME = "p1-to-ep1"
TARGET_FOLDER = "dataset/edit_prompts/"

def get_tree_structure():
    """
    Fetches all keys under TARGET_FOLDER, builds a hierarchical tree,
    calculates recursive file counts, and prints a tree structure.
    """
    try:
        # Initialize S3 client
        client_kwargs = {"region_name": S3_REGION}
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY

        s3 = boto3.client("s3", **client_kwargs)

        print(f"Connecting to bucket: {BUCKET_NAME}")
        print(f"Scanning folder: {TARGET_FOLDER} ...\n")

        paginator = s3.get_paginator("list_objects_v2")
        
        # Tree node structure: {'name': 'dirname', 'direct': 0, 'total': 0, 'children': {}}
        root = {'name': TARGET_FOLDER, 'direct': 0, 'total': 0, 'children': {}}

        file_count_total = 0

        # 1. Build the tree
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=TARGET_FOLDER):
            if "Contents" in page:
                for obj in page["Contents"]:
                    key = obj["Key"]
                    
                    # Remove the base prefix to get relative path
                    if not key.startswith(TARGET_FOLDER):
                        continue
                        
                    rel_path = key[len(TARGET_FOLDER):]
                    if rel_path == "":
                        continue # The root folder itself
                        
                    parts = rel_path.split('/')
                    
                    # Navigate/Build tree
                    current = root
                    
                    # Iterate through parts
                    # If a key ends with '/', it's explicitly a folder. parts will involve an empty string at end.
                    # If it's a file, the last part is the filename.
                    
                    is_folder_obj = key.endswith('/')
                    
                    if is_folder_obj:
                        # It's a directory placeholder
                        path_parts = parts[:-1] # Remove the empty string at end
                        for part in path_parts:
                            if part not in current['children']:
                                current['children'][part] = {'name': part, 'direct': 0, 'total': 0, 'children': {}}
                            current = current['children'][part]
                    else:
                        # It's a file
                        filename = parts[-1]
                        path_parts = parts[:-1]
                        
                        for part in path_parts:
                            if part not in current['children']:
                                current['children'][part] = {'name': part, 'direct': 0, 'total': 0, 'children': {}}
                            current = current['children'][part]
                        
                        current['direct'] += 1
                        file_count_total += 1

        # 2. Calculate recursive counts (depth-first post-order)
        def calc_totals(node):
            s = node['direct']
            for child in node['children'].values():
                s += calc_totals(child)
            node['total'] = s
            return s

        calc_totals(root)

        # 3. Print the tree
        print(f"Total Files Found: {root['total']}\n")
        print(f"{TARGET_FOLDER} (Total: {root['total']}, Direct: {root['direct']})")

        def print_tree_node(node, prefix=""):
            children = sorted(node['children'].keys())
            count = len(children)
            for i, child_name in enumerate(children):
                child_node = node['children'][child_name]
                is_last = (i == count - 1)
                
                connector = "└── " if is_last else "├── "
                
                # Formatting: name [Total: X]
                # If direct > 0, maybe show that too, but usually Total is what matters for "recursive count"
                info = f"[Total: {child_node['total']}]"
                if child_node['direct'] > 0:
                    info += f" (Direct: {child_node['direct']})"
                    
                print(f"{prefix}{connector}{child_name}/ {info}")
                
                extension = "    " if is_last else "│   "
                print_tree_node(child_node, prefix + extension)

        print_tree_node(root)

    except NoCredentialsError:
        print("Error: AWS credentials not found.")
    except ClientError as e:
        print(f"AWS Client Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    get_tree_structure()
