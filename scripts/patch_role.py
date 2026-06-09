import pathlib

f = pathlib.Path('/data/data/com.termux/files/home/ansible/roles/geerlingguy.security/tasks/ssh.yml')
t = f.read_text()

old = ('- name: Ensure SSH daemon is running.\n'
       '  service:\n'
       '    name: "{{ security_sshd_name }}"\n'
       '    state: started\n'
       '    ignore_errors: yes')
new = ('- name: Ensure SSH daemon is running.\n'
       '  service:\n'
       '    name: "{{ security_sshd_name }}"\n'
       '    state: started\n'
       '  ignore_errors: yes')

if old in t:
    f.write_text(t.replace(old, new))
    print("Виправлено.")
else:
    print("Не знайдено, перевір файл вручну.")