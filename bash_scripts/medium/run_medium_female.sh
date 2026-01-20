#!/bin/bash
# Script to run medium female for a specific partition
# Usage: ./run_medium_female.sh <partition_name>
# Example: ./run_medium_female.sh partition_0

if [ -z "$1" ]; then
  echo "Error: No partition supplied."
  echo "Usage: ./run_medium_female.sh <partition_name>"
  exit 1
fi

PARTITION=$1

echo "Starting job for medium female - $PARTITION"

# Ensure we are in the project root (optional check or cd)
# cd /path/to/project

python edit_main.py --model 9b --difficulty medium --gender female --partition "$PARTITION"
