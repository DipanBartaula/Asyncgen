#!/bin/bash
# Script to run hard female for a specific partition
# Usage: ./run_hard_female.sh <partition_name>
# Example: ./run_hard_female.sh partition_0

if [ -z "$1" ]; then
  echo "Error: No partition supplied."
  echo "Usage: ./run_hard_female.sh <partition_name>"
  exit 1
fi

PARTITION=$1

echo "Starting job for hard female - $PARTITION"

# Ensure we are in the project root (optional check or cd)
# cd /path/to/project

python edit_main.py --model 9b --difficulty hard --gender female --partition "$PARTITION"
