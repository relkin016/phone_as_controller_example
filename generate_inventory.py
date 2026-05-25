# generate_inventory.py
import os
import subprocess
import re
import sys

ansible_dir = os.path.join(os.environ['HOME'], 'ansible')
inventory_path = os.path.join(ansible_dir, 'inventory.ini')

vault_pass = None
try:
    result = subprocess.run(
        ['ansible-vault', 'view',
         os.environ['VAULT_FILE'],
         '--vault-password-file', os.environ['VAULT_PASS']],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if line.startswith('ansible_password:'):
            vault_pass = line.split(':', 1)[1].strip()
            break
except Exception:
    pass

if vault_pass:
    print("ansible_password знайдено у Vault")
    pass_line = f'ansible_ssh_pass={vault_pass}\n'
    become_line = f'ansible_become_pass={vault_pass}\n'
else:
    print("ansible_password не у Vault — використовуємо DEFAULT_SSH_PASS")
    default = os.environ['DEFAULT_SSH_PASS']
    pass_line = f'ansible_ssh_pass={default}\n'
    become_line = f'ansible_become_pass={default}\n'

tmp_dir = os.environ.get('TMPDIR', '/tmp')
nmap_file = os.path.join(tmp_dir, 'nmap_scan.txt')

try:
    with open(nmap_file) as f:
        content = f.read()
except FileNotFoundError:
    print("УВАГА: Файл сканування nmap не знайдено!")
    sys.exit(1)

hosts = []
for line in content.splitlines():
    ip_match = re.search(r'Host: (\d+\.\d+\.\d+\.\d+)', line)
    if ip_match and '22/open' in line:
        if any(skip in line for skip in ['Cisco', 'IOS', 'Windows', 'RouterOS']):
            continue
        ip = ip_match.group(1)
        if ip not in hosts:
            hosts.append(ip)

with open(inventory_path, 'w') as f:
    f.write('[scanned]\n')
    for ip in hosts:
        f.write(f'{ip}\n')
    f.write('\n[scanned:vars]\n')
    ansible_user = os.environ.get("ANSIBLE_USER", "admin")
    f.write(f'ansible_user={ansible_user}\n')
    f.write(pass_line)
    f.write(become_line)
    f.write('ansible_ssh_common_args="-o StrictHostKeyChecking=no"\n')

print(f"Знайдено {len(hosts)} хостів з відкритим SSH:")
for h in hosts:
    print(f"  {h}")

if not hosts:
    print("УВАГА: Жодного хоста з відкритим портом 22 не знайдено!")
    sys.exit(1)