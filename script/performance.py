#!/usr/bin/env python3

import os
import csv
import xlsxwriter

path = f"{os.environ['BG_TEST_DIR']}/workload"

workloads = os.listdir(path)
configs = ['BG-1', 'BG-DG', 'BG-SP', 'BG-DGSP', 'BG-2']


# transform flash channel/chip utilization data
for workload in workloads:
    output_dir = f'{path}/{workload}'
    for component in ['channel', 'chip']:
        lines = []
        series = {}
        with open(f'{output_dir}/{component}_utilization.csv') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                lines.append(row)
            for config in configs:
                series[config] = [(line[1], line[2]) for line in lines if line[0] == config]

        with open(f'{output_dir}/{component}_util_transformed.csv', 'w') as f:
            writer = csv.writer(f)
            max_len = max([len(s) for s in series.values()])
            writer.writerow(['time', 'util'] * len(configs))
            for i in range(max_len):
                row = []
                for config in configs:
                    if i < len(series[config]):
                        t, n = series[config][i]
                        row.append(t)
                        row.append(n)
                    else:
                        row.append('')
                        row.append('')
                writer.writerow(row)

# transform hop latency breakdown data
    with open(f'{output_dir}/hop_latency_breakdown.csv') as f:
        lines = []
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            n_hop = len(row) // 2
            for i in range(n_hop):
                config = row[0]
                start_time = float(row[2*i + 1])
                durations = [0] * n_hop
                durations[i] = float(row[2*i + 2]) - float(row[2*i + 1])
                lines.append([config, start_time] + durations)

    with open(f'{output_dir}/hop_latency_breakdown_transformed.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['config', 'start_time'] + [f'hop_{i}' for i in range(n_hop)])
        for line in lines:
            writer.writerow(line)