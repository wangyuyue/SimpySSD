#!/bin/bash

# Define the list of workloads
workload=amazon

bandwidths=(333 800 1600 2400)

for bw in "${bandwidths[@]}"; do
    # Run the Python script with the specified flash channel bandwidth
    $BG_MAIN --workload "$workload" --channel_bw "$bw"
    
    output_dir="$BG_TEST_DIR/channel_bw/${bw}/"
    mkdir -p $output_dir & mv *.csv $output_dir
done