#!/bin/bash

# Define the list of workloads
workloads=("reddit" "amazon" "ml-1m" "ogbn-papers100M" "Protein-PI")

# Loop through each workload in the list
for workload in "${workloads[@]}"; do
    # Run the Python script with the specified workload
    echo "python3 src/main.py --workload $workload"
    python3 src/main.py --workload "$workload"
    
    # Create the directory if it doesn't exist
    mkdir -p "./test/workload/$workload"
    
    # Move the generated CSV files to the corresponding directory
    mv *.csv "./test/workload/$workload/"
done