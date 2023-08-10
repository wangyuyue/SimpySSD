#!/bin/bash

# Define the list of workloads
workload=amazon

n_chips=(2 4 8 16)

for n_chip in "${n_chips[@]}"; do
    # Run the Python script with the specified flash chip number per channel
    python3 src/main.py --workload "$workload" --n_chip "$n_chip"
    
    # Create the directory if it doesn't exist
    mkdir -p "./test/n_chip/$n_chip/"
    
    # Move the generated CSV files to the corresponding directory
    mv *.csv "./test/n_chip/$n_chip/"
done