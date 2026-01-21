import os

# Configuration
difficulties = ["easy", "medium", "hard"]
genders = ["female", "male"]
partitions_count = 7
model = "9b" # User specified 9B for everything in VTON

# Template for .sh script (VTON)
# python vton_main.py --model 9b --difficulty {difficulty} --gender {gender} --partition partition_{p_id}

sh_template = """#!/bin/bash
# VTON Script for {difficulty} {gender} partition {p_id}

python vton_main.py --model {model} --difficulty {difficulty} --gender {gender} --partition partition_{p_id}
"""

def generate_sh_scripts():
    base_dir = "bash_scripts_vton"
    
    for diff in difficulties:
        target_dir = os.path.join(base_dir, diff)
        os.makedirs(target_dir, exist_ok=True)
        
        for gender in genders:
            for p_id in range(partitions_count):
                # run_vton_hard_female_p0.sh
                filename = f"run_vton_{diff}_{gender}_p{p_id}.sh"
                filepath = os.path.join(target_dir, filename)
                
                content = sh_template.format(difficulty=diff, gender=gender, p_id=p_id, model=model)
                
                with open(filepath, "w", newline='\n') as f:
                    f.write(content)
                
                print(f"Generated: {filepath}")

if __name__ == "__main__":
    generate_sh_scripts()
