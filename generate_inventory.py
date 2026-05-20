# generate_inventory.py
import re, os, subprocess, sys

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

# Динамічно визначаємо тимчасову директорію
tmp_dir = os.environ.get('TMPDIR', '/tmp')
nmap_file = os.path.join(tmp_dir, 'nmap_scan.txt')

with open(nmap_file) as f:
    content = f.read()

hosts = []
current_ip = None
for line in content.splitlines():
    ip_match = re.search(r'Host: (\d+\.\d+\.\d+\.\d+)', line)
    if ip_match:
        current_ip = ip_match.group(1)
    if current_ip and ('Ubuntu' in line or 'ubuntu' in line):
        if current_ip not in hosts:
            hosts.append(current_ip)

with open('./inventory.ini', 'w') as f:
    f.write('[scaned]\n')
    for ip in hosts:
        f.write(f'{ip}\n')
    f.write('\n')
    f.write('[scaned:vars]\n')
    f.write(f'ansible_user={os.environ["ANSIBLE_USER"]}\n')
    f.write(pass_line)
    f.write('ansible_become=yes\n')
    f.write('ansible_become_method=sudo\n')
    f.write(become_line)
    f.write('ansible_ssh_common_args=-o StrictHostKeyChecking=no\n')

print(f"Знайдено {len(hosts)} Ubuntu хостів:")
for h in hosts:
    print(f"  {h}")
if not hosts:
    print("УВАГА: Ubuntu хостів не знайдено!")
    sys.exit(1)