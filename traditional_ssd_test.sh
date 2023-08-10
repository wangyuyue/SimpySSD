#!/bin/bash

# Define the list of workloads
workloads=("reddit" "amazon" "ml-1m" "ogbn-papers100M" "Protein-PI")

# Loop through each workload in the list
for workload in "${workloads[@]}"; do
    # Run the Python script with the specified workload using the traditional SSD
    python3 src/main.py --workload "$workload" --ssd traditional_ssd
    
    # Create the directory if it doesn't exist
    mkdir -p "./test/traditional/$workload"
    
    # Move the generated CSV files to the corresponding directory
    mv *.csv "./test/traditional/$workload/"
done