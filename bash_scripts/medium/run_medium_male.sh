#!/bin/bash
# Script to run medium male for a specific partition
# Usage: ./run_medium_male.sh <partition_name>
# Example: ./run_medium_male.sh partition_0

if [ -z "$1" ]; then
  echo "Error: No partition supplied."
  echo "Usage: ./run_medium_male.sh <partition_name>"
  exit 1
fi

PARTITION=$1

echo "Starting job for medium male - $PARTITION"

# Ensure we are in the project root (optional check or cd)
# cd /path/to/project

python edit_main.py --model 9b --difficulty medium --gender male --partition "$PARTITION"
