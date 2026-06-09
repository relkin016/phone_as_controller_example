import pathlib, os, sys

roles_path = os.environ.get('ROLES_PATH', os.path.expanduser('~/ansible/roles'))
f = pathlib.Path(roles_path) / 'geerlingguy.security/tasks/ssh.yml'

if not f.exists():
    print(f"Файл не знайдено: {f}")
    sys.exit(1)

t = f.read_text()
old = ('- name: Ensure SSH daemon is running.\n'
       '  service:\n'
       '    name: "{{ security_sshd_name }}"\n'
       '    state: "{{ security_sshd_state }}"')
new = ('- name: Ensure SSH daemon is running.\n'
       '  service:\n'
       '    name: "{{ security_sshd_name }}"\n'
       '    state: started\n'
       '  ignore_errors: yes')

if old in t:
    f.write_text(t.replace(old, new))
    print("Патч застосовано.")
else:
    print("Вже пропатчено або структура змінилась.")