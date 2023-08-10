#!/bin/bash

# Define the list of workloads
workload=amazon

bandwidths=(333 800 1600 2400)

for bw in "${bandwidths[@]}"; do
    # Run the Python script with the specified flash channel bandwidth
    python3 src/main.py --workload "$workload" --channel_bw "$bw"
    
    # Create the directory if it doesn't exist
    mkdir -p "./test/channel_bw/${bw}/"
    
    # Move the generated CSV files to the corresponding directory
    mv *.csv "./test/channel_bw/${bw}/"
done