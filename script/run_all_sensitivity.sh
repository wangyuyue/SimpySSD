#!/bin/bash

for script in `find ./sensitivity/*.sh`; do
    $script # run the script
done

tests=("batch" "channel_bw" "n_channel" "n_chip" "n_core" "page_size")

# postprocess
for test in "${tests[@]}"; do
    ./postprocess_sensitivity.py -t "$test"
done