#!/bin/bash

tests=("batch" "channel_bw" "n_channel" "n_chip" "n_core" "page_size")

for test in "${tests[@]}"; do
    ./sensitivity.py -t "$test"
done