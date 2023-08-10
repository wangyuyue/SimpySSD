#!/bin/bash

# Define the list of workloads
workload=amazon

page_sizes=(2 4 8 16)

for page_size in "${page_sizes[@]}"; do
    # Run the Python script with the specified embedded core number
    python3 src/main.py --workload "$workload" --page_size "$page_size"
    
    # Create the directory if it doesn't exist
    mkdir -p "./test/page_size/${page_size}"
    
    # Move the generated CSV files to the corresponding directory
    mv *.csv "./test/page_size/${page_size}/"
done