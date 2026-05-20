// Jenkinsfile
pipeline {
    agent any

    triggers {
        GenericTrigger(
            genericVariables: [
                [key: 'ANSIBLE_USER', value: '$.ansible_user', defaultValue: 'ubuntu']
            ],
            token: 'example',
            printContributedVariables: false,
            printPostContent: false
        )
    }

    environment {
        FEATURE_DIR = '.'
        VAULT_PASS  = '../init/.vault_pass'
        VAULT_FILE  = '../init/group_vars/termux/vault.yaml'
        INVENTORY   = './inventory.ini'
        PLAYBOOK    = './playbook.yml'
        MAKEFILE    = './Makefile'
        DEFAULT_SSH_PASS = '1111'
    }

    parameters {
        string(
                name: 'ANSIBLE_USER',
                defaultValue: 'ubuntu',
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
                        # Автовизначення з дефолтного маршруту
                        GW=$(ip route show default | awk '/default/{print $3; exit}')
                        TARGET_SUBNET=$(echo "$GW" | sed 's/\\.[0-9]*$/.0\\/24/')
                        echo "Автовизначено: $TARGET_SUBNET"
                    fi

                    echo "=== nmap сканування $TARGET_SUBNET ==="
                    # Шукаємо хости з відкритим SSH (порт 22)
                    # -sV визначає версію сервісу щоб відфільтрувати Ubuntu
                    nmap -p 22 --open -sV \
                         --script banner \
                         -oG /tmp/nmap_scan.txt \
                         "$TARGET_SUBNET"

                    echo "=== Результат ==="
                    cat /tmp/nmap_scan.txt
                '''
            }
        }

         stage('3. Generate inventory') {
             steps {
                 sh 'python3 ${FEATURE_DIR}/generate_inventory.py'
                 sh "grep -v 'pass' ./inventory.ini"
             }
         }

        stage('4. Copy SSH keys') {
            steps {
                sh '''
                    echo "=== Отримуємо ssh_pass з Vault ==="
                    SSH_PASS=$(ansible-vault view ${VAULT_FILE} \
                        --vault-password-file ${VAULT_PASS} \
                        | awk '/^ssh_pass:/{print $2}')

                    echo "=== Прокидуємо SSH ключ на знайдені хости ==="
                    while IFS= read -r ip; do
                        # Пропускаємо рядки що не є IP
                        [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || continue

                        echo "  → $ip"
                        sshpass -p "$SSH_PASS" \
                            ssh-copy-id \
                                -o StrictHostKeyChecking=no \
                                -o IdentitiesOnly=yes \
                                -i ~/.ssh/id_ed25519.pub \
                                "${ANSIBLE_USER}@${ip}" \
                        && echo "    ✓ ключ скопійовано" \
                        || echo "    ✗ помилка (можливо ключ вже є)"
                    done < <(grep -E '^\d+\.\d+\.\d+\.\d+' ${FEATURE_DIR}/inventory.ini)
                '''
            }
        }

        stage('5. Deploy playbook') {
            steps {
                script {
                    def checkFlag = params.DRY_RUN ? '--check --diff' : ''
                    ansiblePlaybook(
                            playbook: "${env.FEATURE_DIR}/playbook.yml",
                            inventory: "${env.FEATURE_DIR}/inventory.ini",
                            colorized: true,
                            extras: "--vault-password-file ${env.VAULT_PASS} ${checkFlag}"
                    )
                }
            }
        }
    }

    post {
        always {
            sh 'rm -f /tmp/nmap_scan.txt || true'
        }
        success {
            echo "Налаштування завершено успішно."
        }
        failure {
            echo "Помилка. Перевірте логи вище."
        }
    }
}