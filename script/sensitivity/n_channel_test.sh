#!/bin/bash

# Define the list of workloads
workload=amazon

n_channels=(4 8 16 32)

for n_channel in "${n_channels[@]}"; do
    # Run the Python script with the specified flash channel number
    $BG_MAIN --workload "$workload" --n_channel "$n_channel"
    
    output_dir="$BG_TEST_DIR/n_channel/$n_channel/"
    mkdir -p $output_dir & mv *.csv $output_dir
done