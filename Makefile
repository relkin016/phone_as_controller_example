# Makefile

ROLES_PATH   := $(HOME)/ansible/roles
COLLECTIONS_PATH := $(HOME)/ansible/collections
REQUIREMENTS := requirements.yml

SMEE_URL      := https://smee.io/4d4G597DPLT9vOeR
JENKINS_TOKEN := example
SMEE_TARGET   := http://localhost:8080/generic-webhook-trigger/invoke?token=$(JENKINS_TOKEN)
SMEE_LOG      := $(HOME)/.jenkins/logs/smee.log

.PHONY: install clean smee-install smee-start smee-stop

# ── Ansible ───────────────────────────────────────────────────────────────────

install:
	ansible-galaxy install -r $(REQUIREMENTS) -p $(ROLES_PATH)
	ansible-galaxy collection install -r $(REQUIREMENTS) -p $(COLLECTIONS_PATH)
	#$(MAKE) smee-install
	$(MAKE) patch-roles

patch-roles:
	@echo "==> Патчимо geerlingguy.security: ssh state started + ignore_errors..."
	@sed -i \
		's/state: "{{ security_sshd_state }}"/state: started/' \
		$(ROLES_PATH)/geerlingguy.security/tasks/ssh.yml
	@grep -q 'ignore_errors: yes' $(ROLES_PATH)/geerlingguy.security/tasks/ssh.yml || \
		sed -i \
		'/name: Ensure SSH daemon is running/{n;n;n;a\  ignore_errors: yes}' \
		$(ROLES_PATH)/geerlingguy.security/tasks/ssh.yml
	@echo "==> Патч застосовано."
# ── smee ──────────────────────────────────────────────────────────────────────

smee-install:
	@echo "==> Перевірка Node.js..."
	@command -v node >/dev/null 2>&1 || { \
		echo "==> Встановлення Node.js..."; \
		pkg install nodejs -y; \
	}
	@echo "==> Встановлення smee-client..."
	npm install -g smee-client

smee-start:
	@echo "==> Запуск smee listener..."
	@mkdir -p $(dir $(SMEE_LOG))
	@pkill -f 'smee' 2>/dev/null || true
	nohup smee \
		--url $(SMEE_URL) \
		--target "$(SMEE_TARGET)" \
		>> $(SMEE_LOG) 2>&1 &
	@echo "==> smee запущено. Лог: $(SMEE_LOG)"
	@echo "==> URL: $(SMEE_URL)"

smee-stop:
	@echo "==> Зупинка smee..."
	@pkill -f 'smee' 2>/dev/null && echo "==> Зупинено." || echo "==> smee не запущено."