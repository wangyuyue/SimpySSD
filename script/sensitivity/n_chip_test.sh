#!/bin/bash

# Define the list of workloads
workload=amazon

n_chips=(2 4 8 16)

for n_chip in "${n_chips[@]}"; do
    # Run the Python script with the specified flash chip number per channel
    $BG_MAIN --workload "$workload" --n_chip "$n_chip"
    
    output_dir="$BG_TEST_DIR/n_chip/$n_chip/"
    mkdir -p $output_dir & mv *.csv $output_dir
done