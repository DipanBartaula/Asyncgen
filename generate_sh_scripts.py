import os

# Configuration
difficulties = ["easy", "medium", "hard"]
genders = ["female", "male"]
partitions_count = 7

# Template for .sh script (Specific Partition)
sh_template = """#!/bin/bash
# Script to run {difficulty} {gender} partition {p_id} using model {model}

# Ensure we are in the project root (optional check or cd)
# cd /path/to/project

python edit_main.py --model {model} --difficulty {difficulty} --gender {gender} --partition partition_{p_id}
"""

def generate_sh_scripts():
    base_dir = "bash_scripts"
    
    for diff in difficulties:
        target_dir = os.path.join(base_dir, diff)
        os.makedirs(target_dir, exist_ok=True)
        
        # Select Model based on difficulty
        # Easy -> 4b
        # Medium/Hard -> 9b
        model = "4b" if diff == "easy" else "9b"
        
        for gender in genders:
            for p_id in range(partitions_count):
                filename = f"run_{diff}_{gender}_p{p_id}.sh"
                filepath = os.path.join(target_dir, filename)
                
                content = sh_template.format(difficulty=diff, gender=gender, p_id=p_id, model=model)
                
                with open(filepath, "w", newline='\n') as f:
                    f.write(content)
                
                print(f"Generated: {filepath}")

if __name__ == "__main__":
    generate_sh_scripts()
