#!/bin/bash

# Define the list of workloads
workload=amazon

batch_sizes=(32 64 128 256)

for batch_size in "${batch_sizes[@]}"; do
    # Run the Python script with the specified batch size
    echo "$BG_MAIN --workload $workload --batch_size $batch_size"
    $BG_MAIN --workload "$workload" --batch_size "$batch_size"
    
    output_dir="$BG_TEST_DIR/batch/$batch_size/"
    mkdir -p $output_dir & mv *.csv $output_dir
done