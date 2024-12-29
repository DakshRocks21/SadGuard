#!/bin/sh

# make file executable
chmod +x /mnt/file

# get initial processes running using ps
ps -aux > /tmp/initial_processes

echo '## Execution Time'

# run command time /sandbox/run.sh in background and store the result in /tmp/time
timeout 30 bash -c "time /mnt/file > /tmp/time &"

# get final processes running using ps
ps -aux > /tmp/final_processes

# get the difference between the initial and final processes
process_diff=$(diff /tmp/initial_processes /tmp/final_processes)

# store the results in /tmp/results
echo '## Process Difference\n```'
echo "$process_diff"
echo '```\n\n'
echo '---'

echo '## Entropy Analysis\nAnything above 7 is suspicious\n```\n'
EntropyAnalysis -c /mnt/file --no-colors
echo '\n```\n'

# python yara-scanner/yara_main.py --update
# python yara-scanner/yara_main.py --scan-file /mnt/file --gen-report