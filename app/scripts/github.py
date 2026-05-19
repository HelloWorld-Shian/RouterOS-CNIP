"""

功能: 从 APNIC 获取中国 IP 地址段，生成 RouterOS 可用的地址列表文件

"""
import os
import requests
import hashlib
import json
import time
import ipaddress
from datetime import datetime, timedelta, timezone


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(base_dir, "data")

OUTPUT_IPV4 = os.path.join(data_dir, "CN-IPv4.rsc")
OUTPUT_IPV6 = os.path.join(data_dir, "CN-IPv6.rsc")
PREV_IPV4 = os.path.join(data_dir, "previous_CN-IPv4.json")
PREV_IPV6 = os.path.join(data_dir, "previous_CN-IPv6.json")
CHECKSUM_FILE = os.path.join(data_dir, "checksums.sha256")
DIFF_REPORT_FILE = os.path.join(data_dir, "diff_report.txt")

APNIC_STAT_URL = "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-latest"
MAX_RETRIES = 3
RETRY_DELAY = 5

PRIVATE_IPV4_PREFIXES = (
    "10.", "172.16.", "192.168.", "100.64.", "127.", "169.254."
)

def get_china_time():
    return datetime.now(timezone.utc) + timedelta(hours=8)

def fetch_with_retry(url):
    print(f"正在下载 IP 数据: {url}")
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            data = b""
            bar_len = 100

            # 颜色常量
            GREEN = "\033[92m"    # 亮绿色已完成
            GRAY = "\033[90m"     # 灰色未完成
            WHITE = "\033[97m"    # 白色百分比
            END = "\033[0m"       # 恢复默认颜色

            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    data += chunk
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = downloaded / total_size
                        filled = int(bar_len * percent)
                        # 彩色进度条
                        bar = GREEN + "▬" * filled + GRAY + "▭" * (bar_len - filled) + END
                        print(f"\r{bar} {WHITE}{percent*100:.1f}%{END}", end="", flush=True)
                    else:
                        print("\r加载中...", end="", flush=True)

            print("\nIP数据下载完成")
            return data.decode("utf-8")
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise e

def parse_and_aggregate(data):
    ipv4_nets = []
    ipv6_nets = []
    
    for line in data.splitlines():
        p = line.strip().split("|")
        if len(p) < 7 or p[0] != "apnic" or p[1] != "CN":
            continue
        
        try:
            if p[2] == "ipv4":
                network = ipaddress.IPv4Network(f"{p[3]}/{32 - (int(p[4]).bit_length() - 1)}", strict=False)
                ipv4_nets.append(network)
            elif p[2] == "ipv6":
                network = ipaddress.IPv6Network(f"{p[3]}/{p[4]}", strict=False)
                ipv6_nets.append(network)
        except ValueError:
            continue
    
 
    ipv4_filtered = sorted([str(net) for net in ipv4_nets])
    ipv6_final = sorted([str(net) for net in ipv6_nets])
    
    # 私有IPv4过滤
    ipv4_filtered = [ip for ip in ipv4_filtered 
                     if not any(ip.startswith(prefix) for prefix in PRIVATE_IPV4_PREFIXES)]
    
    return ipv4_filtered, ipv6_final

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def save_previous_data(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': get_china_time().isoformat(),
            'data': data
        }, f, indent=2)

def load_previous_data(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f).get('data', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def generate_diff_report(current_ipv4, current_ipv6, prev_ipv4, prev_ipv6):
    report_lines = []
    china_time = get_china_time()
    
    report_lines.append("=" * 60)
    report_lines.append(f"IP 列表变更报告 - {china_time.strftime('%Y-%m-%d %H:%M:%S')} (中国时间)")
    report_lines.append("=" * 60)
    
    added_ipv4 = set(current_ipv4) - set(prev_ipv4)
    removed_ipv4 = set(prev_ipv4) - set(current_ipv4)
    
    report_lines.append("\n[IPv4 变更]")
    if added_ipv4:
        report_lines.append(f"新增 ({len(added_ipv4)} 条):")
        for ip in sorted(added_ipv4):
            report_lines.append(f"  + {ip}")
    if removed_ipv4:
        report_lines.append(f"移除 ({len(removed_ipv4)} 条):")
        for ip in sorted(removed_ipv4):
            report_lines.append(f"  - {ip}")
    if not added_ipv4 and not removed_ipv4:
        report_lines.append("  无变更")
    
    added_ipv6 = set(current_ipv6) - set(prev_ipv6)
    removed_ipv6 = set(prev_ipv6) - set(current_ipv6)
    
    report_lines.append("\n[IPv6 变更]")
    if added_ipv6:
        report_lines.append(f"新增 ({len(added_ipv6)} 条):")
        for ip in sorted(added_ipv6):
            report_lines.append(f"  + {ip}")
    if removed_ipv6:
        report_lines.append(f"移除 ({len(removed_ipv6)} 条):")
        for ip in sorted(removed_ipv6):
            report_lines.append(f"  - {ip}")
    if not added_ipv6 and not removed_ipv6:
        report_lines.append("  无变更")
    
    report_lines.append("\n[统计信息]")
    report_lines.append(f"IPv4: {len(prev_ipv4)} → {len(current_ipv4)} ({len(current_ipv4) - len(prev_ipv4):+d})")
    report_lines.append(f"IPv6: {len(prev_ipv6)} → {len(current_ipv6)} ({len(current_ipv6) - len(prev_ipv6):+d})")
    report_lines.append("=" * 60)
    
    return "\n".join(report_lines)

def write_rsc(path, items, name):
    with open(path, "w", encoding="utf-8") as f:
        china_time = get_china_time()
        f.write(f"# Generated {china_time.strftime('%Y-%m-%d %H:%M:%S')} (China Time)\n")
        f.write(f"# Total entries: {len(items)}\n")
        
        if name == "CN-IPv6":
            f.write("/ipv6 firewall address-list remove [find list=CN-IPv6]\n")
            command_prefix = "/ipv6 firewall address-list add"
        else:
            f.write("/ip firewall address-list remove [find list=CN-IPv4]\n")
            command_prefix = "/ip firewall address-list add"
            
        for i in items:
            f.write(f"{command_prefix} address={i} list={name}\n")

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(current_dir)
    data_dir = os.path.join(app_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    print("正在整理国内公网 IP 列表")

    data = fetch_with_retry(APNIC_STAT_URL)
    current_ipv4, current_ipv6 = parse_and_aggregate(data)

    prev_ipv4 = load_previous_data(PREV_IPV4)
    prev_ipv6 = load_previous_data(PREV_IPV6)

    if current_ipv4 == prev_ipv4 and current_ipv6 == prev_ipv6:
        print("\n✅ IP 列表无变化，跳过生成 RSC 文件")
        return

    diff_report = generate_diff_report(current_ipv4, current_ipv6, prev_ipv4, prev_ipv6)
    with open(DIFF_REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(diff_report)

    print("\n" + "=" * 40)
    print("IP 列表变更摘要")
    print("=" * 40)
    print(f"IPv4: {len(prev_ipv4)} → {len(current_ipv4)} ({len(current_ipv4) - len(prev_ipv4):+d})")
    print(f"IPv6: {len(prev_ipv6)} → {len(current_ipv6)} ({len(current_ipv6) - len(prev_ipv6):+d})")
    print(f"\n详细报告已保存到: {DIFF_REPORT_FILE}")
    print("=" * 40)

    save_previous_data(PREV_IPV4, current_ipv4)
    save_previous_data(PREV_IPV6, current_ipv6)

    write_rsc(OUTPUT_IPV4, current_ipv4, "CN-IPv4")
    write_rsc(OUTPUT_IPV6, current_ipv6, "CN-IPv6")

    checksums = {
        OUTPUT_IPV4: calculate_sha256(OUTPUT_IPV4),
        OUTPUT_IPV6: calculate_sha256(OUTPUT_IPV6),
        PREV_IPV4: calculate_sha256(PREV_IPV4),
        PREV_IPV6: calculate_sha256(PREV_IPV6)
    }

    with open(CHECKSUM_FILE, 'w', encoding='utf-8') as f:
        for file_path, checksum in checksums.items():
            file_name = os.path.basename(file_path)
            f.write(f"{file_name}  {checksum}\n")

    print("\n✅ 生成完成")
    print("输出文件：")
    print(f"  • CN-IPv4.rsc ({len(current_ipv4)} 条)")
    print(f"  • CN-IPv6.rsc ({len(current_ipv6)} 条)")
    print(f"  • 校验文件: {CHECKSUM_FILE}")
    print(f"  • 历史快照已更新")

if __name__ == "__main__":
    main()