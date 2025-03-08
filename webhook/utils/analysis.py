import re

def extract_section(logs: str, section_title: str) -> str:
    """
    Extracts the content after a markdown header with the given title, up until the next header or end-of-file.
    Expected log format example:
    
    ## Mitmproxy Log (HTTP/HTTPS flows)
    <content to extract>
    ## Tcpdump Log (All network traffic)
    
    Returns:
        str: The extracted content, or an empty string if the section was not found.
    """
    # Match the header, optional whitespace, a newline, then capture until the next header line or end-of-string.
    pattern = re.compile(rf"## {re.escape(section_title)}\s*\n(.*?)(?=\n## |\Z)", re.DOTALL)
    match = pattern.search(logs)
    if match:
        return match.group(1).strip()
    return ""

# logs = """
# ## Code Output
# ```
# ============================= test session starts ==============================
# platform linux -- Python 3.10.16, pytest-8.3.5, pluggy-1.5.0 -- /usr/local/bin/python3.10
# cachedir: .pytest_cache
# rootdir: /app
# collecting ... collected 2 items

# tests/test_app.py::test_create_note PASSED                               [ 50%]
# tests/test_app.py::test_healthcheck PASSED                               [100%]

# ============================== 2 passed in 5.31s ===============================
# ```
# ---
# ## Code Error
# ```
# ```
# ---
# ## Mitmproxy Log (HTTP/HTTPS flows)
# ```
# [13:33:19.834] Transparent Proxy listening at *:8080.
# ```
# ---
# ## Tcpdump Log (All network traffic)
# ```
# tcpdump: data link type LINUX_SLL2
# tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
# listening on any, link-type LINUX_SLL2 (Linux cooked v2), snapshot length 262144 bytes
# 13:33:19.578118 eth0  M   IP6 :: > ff02::16: HBH ICMP6, multicast listener report v2, 1 group record(s), length 28
# 13:33:19.689406 eth0  Out ARP, Request who-has 172.17.0.1 tell 172.17.0.2, length 28
# 13:33:19.689465 eth0  In  ARP, Reply 172.17.0.1 is-at 02:42:ea:4d:10:58, length 28
# 13:33:19.689470 eth0  Out IP 172.17.0.2.42088 > 192.168.0.1.53: 11258+ A? attacker.com. (30)
# 13:33:19.872136 eth0  M   IP6 :: > ff02::1:ffd4:b572: ICMP6, neighbor solicitation, who has fe80::fc8f:7fff:fed4:b572, length 32
# 13:33:19.932645 eth0  In  IP 192.168.0.1.53 > 172.17.0.2.42088: 11258 1/0/0 A 209.196.146.115 (46)
# 13:33:19.932853 eth0  Out IP 172.17.0.2.45778 > 209.196.146.115.31337: Flags [S], seq 3219741925, win 64240, options [mss 1460,sackOK,TS val 3449673290 ecr 0,nop,wscale 7], length 0
# 13:33:20.248115 eth0  M   IP6 fe80::42:eaff:fe4d:1058 > ff02::16: HBH ICMP6, multicast listener report v2, 3 group record(s), length 68
# 13:33:20.487735 eth0  M   IP 172.17.0.1.5353 > 224.0.0.251.5353: 0 PTR (QM)? _googlecast._tcp.local. (40)
# 13:33:20.487936 eth0  M   IP 172.17.0.1.5353 > 224.0.0.251.5353: 0 PTR (QM)? _googlecast._tcp.local. (40)
# 13:33:20.888276 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572 > ff02::16: HBH ICMP6, multicast listener report v2, 1 group record(s), length 28
# 13:33:20.888290 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572 > ff02::2: ICMP6, router solicitation, length 16
# 13:33:20.891161 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572 > ff02::16: HBH ICMP6, multicast listener report v2, 1 group record(s), length 28
# 13:33:20.952074 eth0  Out IP 172.17.0.2.45778 > 209.196.146.115.31337: Flags [S], seq 3219741925, win 64240, options [mss 1460,sackOK,TS val 3449674310 ecr 0,nop,wscale 7], length 0
# 13:33:20.989283 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572.5353 > ff02::fb.5353: 0 [2q] PTR (QM)? _ipps._tcp.local. PTR (QM)? _ipp._tcp.local. (45)
# 13:33:21.024133 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572 > ff02::16: HBH ICMP6, multicast listener report v2, 2 group record(s), length 48
# 13:33:21.131342 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572.5353 > ff02::fb.5353: 0 [2q] [2n] ANY (QM)? 2.7.5.b.4.d.e.f.f.f.f.7.f.8.c.f.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa. ANY (QM)? linux.local. (149)
# 13:33:21.152073 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572 > ff02::16: HBH ICMP6, multicast listener report v2, 1 group record(s), length 28
# 13:33:21.382198 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572.5353 > ff02::fb.5353: 0 [2q] [2n] ANY (QM)? 2.7.5.b.4.d.e.f.f.f.f.7.f.8.c.f.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa. ANY (QM)? linux.local. (149)
# 13:33:21.488385 eth0  M   IP 172.17.0.1.5353 > 224.0.0.251.5353: 0 PTR (QM)? _googlecast._tcp.local. (40)
# 13:33:21.488590 eth0  M   IP 172.17.0.1.5353 > 224.0.0.251.5353: 0 PTR (QM)? _googlecast._tcp.local. (40)
# 13:33:21.632953 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572.5353 > ff02::fb.5353: 0 [2q] [2n] ANY (QM)? 2.7.5.b.4.d.e.f.f.f.f.7.f.8.c.f.0.0.0.0.0.0.0.0.0.0.0.0.0.8.e.f.ip6.arpa. ANY (QM)? linux.local. (149)
# 13:33:21.833181 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572.5353 > ff02::fb.5353: 0*- [0q] 2/0/0 (Cache flush) PTR linux.local., (Cache flush) AAAA fe80::fc8f:7fff:fed4:b572 (137)
# 13:33:21.976069 eth0  Out IP 172.17.0.2.45778 > 209.196.146.115.31337: Flags [S], seq 3219741925, win 64240, options [mss 1460,sackOK,TS val 3449675334 ecr 0,nop,wscale 7], length 0
# 13:33:21.990141 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572.5353 > ff02::fb.5353: 0 [2q] PTR (QM)? _ipps._tcp.local. PTR (QM)? _ipp._tcp.local. (45)
# 13:33:22.670695 eth0  B   IP 172.17.0.1.57621 > 172.17.255.255.57621: UDP, length 44
# 13:33:22.892572 eth0  M   IP 172.17.0.1.43463 > 239.255.255.250.1900: UDP, length 168
# 13:33:23.000071 eth0  Out IP 172.17.0.2.45778 > 209.196.146.115.31337: Flags [S], seq 3219741925, win 64240, options [mss 1460,sackOK,TS val 3449676358 ecr 0,nop,wscale 7], length 0
# 13:33:23.028326 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572.5353 > ff02::fb.5353: 0*- [0q] 2/0/0 (Cache flush) PTR linux.local., (Cache flush) AAAA fe80::fc8f:7fff:fed4:b572 (137)
# 13:33:23.893859 eth0  M   IP 172.17.0.1.43463 > 239.255.255.250.1900: UDP, length 168
# 13:33:23.992256 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572.5353 > ff02::fb.5353: 0 [2q] PTR (QM)? _ipps._tcp.local. PTR (QM)? _ipp._tcp.local. (45)
# 13:33:24.024078 eth0  Out IP 172.17.0.2.45778 > 209.196.146.115.31337: Flags [S], seq 3219741925, win 64240, options [mss 1460,sackOK,TS val 3449677382 ecr 0,nop,wscale 7], length 0
# 13:33:24.728088 eth0  M   IP6 fe80::fc8f:7fff:fed4:b572 > ff02::2: ICMP6, router solicitation, length 16
# 13:33:24.895090 eth0  M   IP 172.17.0.1.43463 > 239.255.255.250.1900: UDP, length 168

# 34 packets captured
# 36 packets received by filter
# 0 packets dropped by kernel
# ```
# ---
# ## Network Difference (Initial vs Final)
# ```

# ```
# ---
# """

# print(extract_section(logs, "Code Output"))
# print(extract_section(logs, "Code Error"))
# print(extract_section(logs, "Mitmproxy Log (HTTP/HTTPS flows)"))
# print(extract_section(logs, "Tcpdump Log (All network traffic)"))
# print(extract_section(logs, "Network Difference (Initial vs Final)"))