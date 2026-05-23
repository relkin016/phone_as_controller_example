// Jenkinsfile
pipeline {
    agent any

    triggers {
        GenericTrigger(
            genericVariables: [
                [key: 'ANSIBLE_USER', value: '$.ansible_user', defaultValue: 'roman']
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
            defaultValue: 'admin',
            description: 'SSH користувач на цільових хостах'
        )
        string(
            name: 'SUBNET',
            defaultValue: '',
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
                    echo "=== Встановлення системних залежностей Termux ==="
                    pkg install -y nmap iproute2 sshpass
                    echo "=== make install ==="
                    cd ${FEATURE_DIR}
                    make install
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
                 | awk '/^ssh_pass:/{print $2}')

             grep -E '^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+' "$INVENTORY" | while IFS= read -r ip; do
                 echo "  → $ip"
                 sshpass -p "$SSH_PASS" \
                     ssh-copy-id \
                         -o StrictHostKeyChecking=no \
                         -o IdentitiesOnly=yes \
                         -i ~/.ssh/id_ed25519.pub \
                         "${ANSIBLE_USER}@${ip}" \
                 && echo "    ✓ ключ скопійовано" \
                 || echo "    ✗ помилка"
             done
         '''
     }
 }

        stage('5. Deploy playbook') {
            steps {
                script {
                    def hostCount = sh(
                        script: "grep -c -E '^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+' ${env.INVENTORY} || echo 5",
                        returnStdout: true
                    ).trim()
                    echo "Знайдено ${hostCount} вузлів. Запускаємо Ansible з ${hostCount} паралельними потоками."
                    def checkFlag = params.DRY_RUN ? '--check --diff' : ''
                    ansiblePlaybook(
                        playbook: "${env.FEATURE_DIR}/playbook.yml",
                        inventory: env.INVENTORY,
                        colorized: true,
                        extras: "--vault-password-file ${env.VAULT_PASS} -f ${hostCount} ${checkFlag}"
                    )
                }
            }
        }
    } // Тепер блок stages закривається правильно тут

    post {
        always {
            node('') {
                sh 'rm -f ${TMPDIR:-/tmp}/nmap_scan.txt || true'
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