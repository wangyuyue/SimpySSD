#!/bin/bash

# Define the list of workloads
workload=amazon

batch_sizes=(32 64 128 256)

for batch_size in "${batch_sizes[@]}"; do
    # Run the Python script with the specified batch size
    echo "python3 src/main.py --workload $workload --batch_size $batch_size"
    python3 src/main.py --workload "$workload" --batch_size "$batch_size"
    
    # Create the directory if it doesn't exist
    mkdir -p "./test/batch/$batch_size"
    
    # Move the generated CSV files to the corresponding directory
    mv *.csv "./test/batch/$batch_size/"
done