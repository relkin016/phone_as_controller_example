// Jenkinsfile
pipeline {
    agent any

    triggers {
        GenericTrigger(
            genericVariables: [
                [key: 'ANSIBLE_USER', value: '$.ansible_user', defaultValue: 'admin']
            ],
            token: 'example',
            printContributedVariables: false,
            printPostContent: false
        )
    }

    environment {
        FEATURE_DIR      = '.'
        VAULT_PASS       = "${env.HOME}/ansible/.vault_pass"
        ANSIBLE_CONFIG   = "${env.HOME}/ansible/ansible.cfg"
        VAULT_FILE       = "${env.HOME}/ansible/group_vars/all/vault.yaml"
        INVENTORY        = "${env.HOME}/ansible/inventory.ini"
        ANSIBLE_USER     = "${params.ANSIBLE_USER ?: 'admin'}"
        PLAYBOOK         = './playbook.yml'
        DEFAULT_SSH_PASS = '1111'
    }

    parameters {
        string(
            name: 'ANSIBLE_USER',
            defaultValue: 'relkin',
            description: 'SSH користувач на цільових хостах'
        )
        string(
            name: 'SUBNET',
            defaultValue: '192.168.177.0/24',
            description: 'Підмережа для сканування (напр. 192.168.1.0/24). Порожньо = автовизначення'
        )
        booleanParam(
            name: 'DRY_RUN',
            defaultValue: false,
            description: 'ansible --check --diff без реальних змін'
        )
    }

    stages {
        stage('1. Install requirements') {
            steps {
                sh '''
                    pkg install -y nmap iproute2 sshpass
                    cd ${FEATURE_DIR}
                    make install
                    if [ ! -f ~/.ssh/id_ed25519 ]; then
                        ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""
                    fi
                '''
            }
        }

        stage('2. nmap scan') {
            steps {
                sh '''
                    echo "=== Визначення підмережі ==="
                    if [ -n "$SUBNET" ]; then
                        TARGET_SUBNET="$SUBNET"
                    else
                        # Використовуємо ip a для пошуку глобальної IPv4 адреси (ігноруємо lo)
                        GW=$(ip -4 addr show scope global | awk '/inet /{print $2}' | cut -d/ -f1 | head -n1)

                        if [ -z "$GW" ]; then
                            echo "Помилка: не вдалося знайти IP-адресу через 'ip a'."
                            exit 1
                        fi

                        # Перетворюємо IP (напр. 192.168.100.87) на підмережу (192.168.100.0/24)
                        TARGET_SUBNET=$(echo "$GW" | sed 's/\\.[0-9]*$/.0\\/24/')
                        echo "Ваш IP у Termux: $GW"
                        echo "Автовизначено підмережу: $TARGET_SUBNET"
                    fi

                    # Тимчасовий файл у правильній директорії Termux
                    NMAP_OUT="${TMPDIR:-/tmp}/nmap_scan.txt"

                    echo "=== nmap сканування $TARGET_SUBNET ==="
                    nmap -p 22 --open -sV \
                         --script banner \
                         -oG "$NMAP_OUT" \
                         "$TARGET_SUBNET"

                    echo "=== Результат ==="
                    cat "$NMAP_OUT"
                '''
            }
        }

        stage('3. Generate inventory') {
            steps {
                sh 'python3 ${FEATURE_DIR}/generate_inventory.py'
                sh "grep -v 'pass' ${env.HOME}/ansible/inventory.ini"
            }
        }

        stage('4. Copy SSH keys') {
            steps {
                sh '''#!/bin/bash
                    SSH_PASS=$(ansible-vault view ${VAULT_FILE} \
                        --vault-password-file ${VAULT_PASS} \
                        | awk '/^ssh_pass:/{print $2}' | tr -d '\r')

                    if [ -z "$SSH_PASS" ]; then
                        echo "✗ Пароль не знайдено!"
                        exit 1
                    fi

                    PUB_KEY=$(cat ~/.ssh/id_ed25519.pub)
                    TOTAL=0
                    SUCCESS=0
                    TMPDIR="${TMPDIR:-/data/data/com.termux/files/usr/tmp}"
                    INI_FILE="${TMPDIR}/successful_hosts.ini"
                    KEY_PATH="$HOME/.ssh/id_ed25519"

                    # ✅ Діагностика inventory
                    echo "--- INVENTORY ($INVENTORY) ---"
                    cat "$INVENTORY"
                    echo "--- GREP RESULT ---"
                    # ✅ Витягуємо IP з будь-якого місця рядка (ansible_host=X або просто X)
                    grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' "$INVENTORY" || echo "IP не знайдено!"
                    echo "---"

                    printf "[scanned]\n" > "${INI_FILE}"

                    # ✅ grep -oE витягує IP навіть якщо він не на початку рядка
                    while IFS= read -r ip; do
                        TOTAL=$((TOTAL + 1))
                        echo "  → $ip"

                        OUTPUT=$(ssh \
                            -o StrictHostKeyChecking=no \
                            -o PasswordAuthentication=no \
                            -o PubkeyAuthentication=yes \
                            -o ConnectTimeout=5 \
                            -i "${KEY_PATH}" \
                            "${ANSIBLE_USER}@${ip}" \
                            "echo OK" \
                            </dev/null 2>&1)

                        if echo "$OUTPUT" | grep -q "^OK"; then
                            echo "    ✓ Ключ вже є"
                            SUCCESS=$((SUCCESS + 1))
                            echo "$ip" >> "${INI_FILE}"
                            continue
                        fi

                        OUTPUT=$(sshpass -p "$SSH_PASS" ssh \
                            -o StrictHostKeyChecking=no \
                            -o IdentitiesOnly=yes \
                            -o PasswordAuthentication=yes \
                            -o PubkeyAuthentication=no \
                            -o ConnectTimeout=5 \
                            -o KexAlgorithms=+diffie-hellman-group1-sha1,diffie-hellman-group14-sha1 \
                            "${ANSIBLE_USER}@${ip}" \
                            "mkdir -p ~/.ssh && chmod 700 ~/.ssh && \
                             grep -qF '${PUB_KEY}' ~/.ssh/authorized_keys 2>/dev/null || \
                             echo '${PUB_KEY}' >> ~/.ssh/authorized_keys && \
                             chmod 600 ~/.ssh/authorized_keys && echo OK" \
                            </dev/null 2>&1)

                        if echo "$OUTPUT" | grep -q "^OK"; then
                            echo "    ✓ Ключ скопійовано"
                            SUCCESS=$((SUCCESS + 1))
                            echo "$ip" >> "${INI_FILE}"
                        else
                            echo "    ✗ Помилка: $(echo "$OUTPUT" | head -2)"
                        fi

                    done < <(grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' "$INVENTORY")

                    printf "\n[scanned:vars]\n" >> "${INI_FILE}"
                    printf "ansible_user=%s\n" "${ANSIBLE_USER}" >> "${INI_FILE}"
                    printf "ansible_ssh_private_key_file=%s\n" "${KEY_PATH}" >> "${INI_FILE}"
                    printf "ansible_ssh_common_args=-o StrictHostKeyChecking=no\n" >> "${INI_FILE}"

                    echo ""
                    echo "Результат: ${SUCCESS}/${TOTAL} хостів"

                    # ✅ Forks мінімум 1, навіть якщо 0 хостів — щоб ansible не падав
                    FORKS=$SUCCESS
                    if [ "$FORKS" -lt 1 ]; then
                        FORKS=1
                    fi
                    echo "$SUCCESS" > "${TMPDIR}/success_count.txt"
                    echo "$FORKS"   > "${TMPDIR}/forks_count.txt"

                    echo "--- Фінальний inventory ---"
                    cat "${INI_FILE}"
                '''
            }
        }

        stage('5. Deploy playbook') {
            steps {
                script {
                    def success = sh(script: "cat ${TMPDIR}/success_count.txt", returnStdout: true).trim().toInteger()
                    def forks   = sh(script: "cat ${TMPDIR}/forks_count.txt",   returnStdout: true).trim().toInteger()
                    echo "Успішно приєднано ${success} вузлів."
                    ansiblePlaybook(
                        playbook: './playbook.yml',
                        inventory: "${TMPDIR}/successful_hosts.ini",
                        vaultCredentialsId: '',
                        extraVars: [ansible_become_password: '1111'],
                        forks: forks,   // ✅ завжди >= 1
                        extras: "--vault-password-file ${VAULT_PASS}"
                    )
                }
            }
        }
    }

    post {
        always {
            node('') {
            sh 'rm -f "${TMPDIR}/nmap_scan.txt" "${TMPDIR}/success_count.txt" "${TMPDIR}/successful_hosts.ini" || true'
            }
        }
        success {
            echo "Налаштування завершено успішно."
        }
        failure {
            echo "Помилка. Перевірте логи вище."
        }
    }
}