import os

# Configuration
difficulties = ["easy", "medium", "hard"]
genders = ["female", "male"]

# Template for .sh script (Parameterized)
sh_template = """#!/bin/bash
# Script to run {difficulty} {gender} for a specific partition
# Usage: ./run_{difficulty}_{gender}.sh <partition_name>
# Example: ./run_{difficulty}_{gender}.sh partition_0

if [ -z "$1" ]; then
  echo "Error: No partition supplied."
  echo "Usage: ./run_{difficulty}_{gender}.sh <partition_name>"
  exit 1
fi

PARTITION=$1

echo "Starting job for {difficulty} {gender} - $PARTITION"

# Ensure we are in the project root (optional check or cd)
# cd /path/to/project

python edit_main.py --model 9b --difficulty {difficulty} --gender {gender} --partition "$PARTITION"
"""

def generate_sh_scripts():
    base_dir = "bash_scripts"
    
    # Clean up old files if needed manually or just overwrite logic
    
    for diff in difficulties:
        target_dir = os.path.join(base_dir, diff)
        os.makedirs(target_dir, exist_ok=True)
        
        for gender in genders:
            # Create ONE script per gender/difficulty that takes an argument
            filename = f"run_{diff}_{gender}.sh"
            filepath = os.path.join(target_dir, filename)
            
            content = sh_template.format(difficulty=diff, gender=gender)
            
            with open(filepath, "w", newline='\n') as f:
                f.write(content)
            
            print(f"Generated: {filepath}")

if __name__ == "__main__":
    generate_sh_scripts()
