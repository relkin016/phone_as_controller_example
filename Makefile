# Makefile

ROLES_PATH   := $(HOME)/ansible/roles
REQUIREMENTS := requirements.yml

SMEE_URL      := https://smee.io/4d4G597DPLT9vOeR
JENKINS_TOKEN := example
SMEE_TARGET   := http://localhost:8080/generic-webhook-trigger/invoke?token=$(JENKINS_TOKEN)
SMEE_LOG      := $(HOME)/.jenkins/logs/smee.log

.PHONY: install clean smee-install smee-start smee-stop

# ── Ansible ───────────────────────────────────────────────────────────────────

install:
	@echo "==> Встановлення Ansible ролей з Galaxy..."
	ansible-galaxy install -r $(REQUIREMENTS) -p $(ROLES_PATH) --force
	@echo "==> Патч devsec.ssh_hardening для Jinja2 3.1.4+..."
	sed -i 's/#jinja2: trim_blocks: "true"/#jinja2: trim_blocks: true/' \
		$(ROLES_PATH)/devsec.ssh_hardening/templates/opensshd.conf.j2
	sed -i 's/lstrip_blocks: "true"/lstrip_blocks: true/' \
		~/ansible/roles/devsec.ssh_hardening/templates/opensshd.conf.j2
	#$(MAKE) smee-install

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