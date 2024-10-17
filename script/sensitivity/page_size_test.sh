#!/bin/bash

# Define the list of workloads
workload=amazon

page_sizes=(2 4 8 16)

for page_size in "${page_sizes[@]}"; do
    # Run the Python script with the specified embedded core number
    $BG_MAIN --workload "$workload" --page_size "$page_size"
    
    output_dir="$BG_TEST_DIR/page_size/${page_size}/"
    mkdir -p $output_dir & mv *.csv $output_dir
done