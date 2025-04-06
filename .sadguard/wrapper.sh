#!/bin/bash

export PYTHONPATH=/app:$PYTHONPATH

# Capture initial state.
ps -aux > /tmp/initial_processes
netstat -tunapl > /tmp/initial_network

# Clean or create log files.
: > /tmp/mitm_log
: > /tmp/tcpdump_log
: > /tmp/code_output
: > /tmp/code_error

# Start mitmdump in transparent mode (for HTTP/HTTPS flows) with a 60-second timeout.
# Increase verbosity so we see flow details.
timeout 60 mitmdump --mode transparent --listen-port 8080 --set console_flow_detail=3 > /tmp/mitm_log 2>&1 &
mitm_pid=$!

# Start tcpdump to capture all network traffic (this will catch raw socket connections too).
tcpdump -i any -nn -l > /tmp/tcpdump_log 2>&1 &
tcpdump_pid=$!

# Set up iptables rules to redirect outgoing HTTP (port 80) and HTTPS (port 443) traffic to port 8080.
iptables -t nat -A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 8080
iptables -t nat -A OUTPUT -p tcp --dport 443 -j REDIRECT --to-port 8080

# Run the test command (using the DEFAULT_CMD environment variable) with a timeout of 30 seconds.
timeout 30 bash -c "$DEFAULT_CMD" > /tmp/code_output 2> /tmp/code_error
test_ret=$?

# Clean up iptables rules.
iptables -t nat -D OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 8080
iptables -t nat -D OUTPUT -p tcp --dport 443 -j REDIRECT --to-port 8080

# Stop mitmdump and tcpdump if still running.
kill $mitm_pid 2>/dev/null
wait $mitm_pid 2>/dev/null

kill $tcpdump_pid 2>/dev/null
wait $tcpdump_pid 2>/dev/null

# Capture final state.
netstat -tunapl > /tmp/final_network
ps -aux > /tmp/final_processes

# Output captured logs.
echo "## Code Output"
cat /tmp/code_output
echo '---'

echo "## Code Error"
cat /tmp/code_error
echo '---'

echo "## Mitmproxy Log (HTTP/HTTPS flows)"
cat /tmp/mitm_log
echo '---'

echo "## Tcpdump Log (All network traffic)"
cat /tmp/tcpdump_log
echo '---'

network_diff=$(diff /tmp/initial_network /tmp/final_network)
echo "## Network Difference (Initial vs Final)"
echo "$network_diff"
echo '---'

exit $test_ret
