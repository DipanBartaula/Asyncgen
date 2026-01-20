#!/bin/bash
# Script to run easy female for a specific partition
# Usage: ./run_easy_female.sh <partition_name>
# Example: ./run_easy_female.sh partition_0

if [ -z "$1" ]; then
  echo "Error: No partition supplied."
  echo "Usage: ./run_easy_female.sh <partition_name>"
  exit 1
fi

PARTITION=$1

echo "Starting job for easy female - $PARTITION"

# Ensure we are in the project root (optional check or cd)
# cd /path/to/project

python edit_main.py --model 9b --difficulty easy --gender female --partition "$PARTITION"
