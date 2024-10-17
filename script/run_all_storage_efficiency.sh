#!/bin/bash

# Define the list of workloads
workloads=("reddit" "amazon" "ml-1m" "ogbn-papers100M" "Protein-PI")

# Loop through each workload in the list
for workload in "${workloads[@]}"; do
    # Run the Python script with the specified workload
    echo "./storage_efficiency.py --workload $workload"
    ./storage_efficiency.py --workload "$workload"
done