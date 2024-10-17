#!/usr/bin/env python3

import os
import argparse
import csv

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--test_name')

args = parser.parse_args()
path = f"{os.environ['BG_TEST_DIR']}/{args.test_name}"

latency = {}

max_latency = 0

settings = sorted([int(dir) for dir in os.listdir(path) if os.path.isdir(f'{path}/{dir}')])


for setting in settings:
    latency[setting] = {}
    with open(f'{path}/{setting}/speedup.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        for row in reader:
            if row[0] == 'CC':
                continue
            lat = float(row[1])
            if args.test_name == 'batch':
                lat /= setting
            max_latency = max(max_latency, lat)
            latency[setting][row[0]] = lat

normalized_throughput = {}
for setting in settings:
    normalized_throughput[setting] = {}
    for config, lat in latency[setting].items():
        normalized_throughput[setting][config] = max_latency / lat

# write normalized_throughput to csv, header is test_name, latency.keys()
with open(f'{path}/normalized_throughput.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow([f'{args.test_name}'] + list(latency[settings[0]].keys()))
    for dir in settings:
        row = [dir]
        for config, throughput in normalized_throughput[dir].items():
            row.append(throughput)
        writer.writerow(row)
