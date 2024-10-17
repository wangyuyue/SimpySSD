#!/bin/bash

# Define the list of workloads
workload=amazon

n_cores=(1 2 3 4 5 6 7 8)

for n_core in "${n_cores[@]}"; do
    # Run the Python script with the specified embedded core number
    $BG_MAIN --workload "$workload" --n_core "$n_core"
    
    output_dir="$BG_TEST_DIR/n_core/$n_core/"
    mkdir -p $output_dir & mv *.csv $output_dir
done