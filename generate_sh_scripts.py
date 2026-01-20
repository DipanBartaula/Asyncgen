import os

# Configuration
difficulties = ["easy", "medium", "hard"]
genders = ["female", "male"]
partitions_count = 7

# Template for .sh script (Specific Partition)
sh_template = """#!/bin/bash
# Script to run {difficulty} {gender} partition {p_id}

# Ensure we are in the project root (optional check or cd)
# cd /path/to/project

python edit_main.py --model 9b --difficulty {difficulty} --gender {gender} --partition partition_{p_id}
"""

def generate_sh_scripts():
    base_dir = "bash_scripts"
    
    for diff in difficulties:
        target_dir = os.path.join(base_dir, diff)
        os.makedirs(target_dir, exist_ok=True)
        
        for gender in genders:
            for p_id in range(partitions_count):
                filename = f"run_{diff}_{gender}_p{p_id}.sh"
                filepath = os.path.join(target_dir, filename)
                
                content = sh_template.format(difficulty=diff, gender=gender, p_id=p_id)
                
                with open(filepath, "w", newline='\n') as f:
                    f.write(content)
                
                print(f"Generated: {filepath}")

if __name__ == "__main__":
    generate_sh_scripts()
