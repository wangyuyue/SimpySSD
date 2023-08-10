#!/bin/bash

# Define the list of workloads
workload=amazon

n_channels=(4 8 16 32)

for n_channel in "${n_channels[@]}"; do
    # Run the Python script with the specified flash channel number
    python3 src/main.py --workload "$workload" --n_channel "$n_channel"
    
    # Create the directory if it doesn't exist
    mkdir -p "./test/n_channel/$n_channel/"
    
    # Move the generated CSV files to the corresponding directory
    mv *.csv "./test/n_channel/$n_channel/"
done