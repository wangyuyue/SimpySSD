#!/bin/bash

# Define the list of workloads
workloads=("reddit" "amazon" "ml-1m" "ogbn-papers100M" "Protein-PI")

# Loop through each workload in the list
for workload in "${workloads[@]}"; do
    # Run the Python script with the specified workload
    echo "$BG_MAIN --workload $workload"
    $BG_MAIN --workload "$workload"
    
    output_dir="$BG_TEST_DIR/workload/$workload/"
    mkdir -p $output_dir & mv *.csv $output_dir
done