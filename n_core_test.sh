#!/bin/bash

# Define the list of workloads
workload=amazon

n_cores=(1 2 3 4 5 6 7 8)

for n_core in "${n_cores[@]}"; do
    # Run the Python script with the specified embedded core number
    python3 src/main.py --workload "$workload" --n_core "$n_core"
    
    # Create the directory if it doesn't exist
    mkdir -p "./test/n_core/$n_core"
    
    # Move the generated CSV files to the corresponding directory
    mv *.csv "./test/n_core/$n_core/"
done