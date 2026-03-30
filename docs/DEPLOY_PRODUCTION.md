# 🚀 Deploy em Produção - Hetzner VPS

Guia completo para deploy do TactoFlow em uma VPS Hetzner CX33.

---

## 📋 Índice

1. [Especificações do Servidor](#1-especificações-do-servidor)
2. [Setup Inicial do Servidor](#2-setup-inicial-do-servidor)
3. [Segurança do Servidor](#3-segurança-do-servidor)
4. [Instalação do Docker](#4-instalação-do-docker)
5. [Configuração do Projeto](#5-configuração-do-projeto)
6. [SSL/HTTPS com Let's Encrypt](#6-sslhttps-com-lets-encrypt)
7. [Deploy da Aplicação](#7-deploy-da-aplicação)
8. [Configuração de DNS](#8-configuração-de-dns)
9. [Monitoramento e Logs](#9-monitoramento-e-logs)
10. [Backup Automático](#10-backup-automático)
11. [CI/CD com GitHub Actions](#11-cicd-com-github-actions)
12. [Manutenção e Troubleshooting](#12-manutenção-e-troubleshooting)
13. [Checklist Final](#13-checklist-final)

---

## 1. Especificações do Servidor

### Hetzner CX33
| Recurso | Especificação |
|---------|---------------|
| **vCPU** | 4 cores |
| **RAM** | 8 GB |
| **Storage** | 80 GB NVMe SSD |
| **Tráfego** | 20 TB/mês |
| **OS Recomendado** | Ubuntu 22.04 LTS |

### Distribuição de Recursos (Estimada)
```
┌─────────────────────────────────────────────────────────────┐
│ MEMÓRIA (8GB)                                               │
├─────────────────────────────────────────────────────────────┤
│ PostgreSQL    │ 1.5 GB (pool + cache)                       │
│ Redis         │ 256 MB (cache + buffers)                    │
│ API (4 workers)│ 2 GB (500MB x 4 workers)                   │
│ Nginx         │ 128 MB                                      │
│ Sistema       │ 1 GB                                        │
│ Reserva       │ ~3 GB (picos, migrations, etc.)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Setup Inicial do Servidor

### 2.1 Criar a VPS na Hetzner

1. Acesse [Hetzner Cloud Console](https://console.hetzner.cloud/)
2. Crie um novo projeto
3. Adicione um servidor:
   - **Localização**: Nuremberg (eu-central) ou Ashburn (us-east)
   - **Imagem**: Ubuntu 22.04
   - **Tipo**: CX33
   - **SSH Key**: Adicione sua chave pública

### 2.2 Primeiro Acesso

```bash
# Conectar ao servidor (substitua pelo IP real)
ssh root@YOUR_SERVER_IP

# Atualizar sistema
apt update && apt upgrade -y

# Instalar utilitários essenciais
apt install -y \
    curl \
    wget \
    git \
    htop \
    vim \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    fail2ban \
    ufw
```

### 2.3 Criar Usuário de Deploy (NÃO usar root)

```bash
# Criar usuário 'deploy'
adduser deploy

# Adicionar ao grupo sudo
usermod -aG sudo deploy

# Copiar chave SSH do root para o novo usuário
mkdir -p /home/deploy/.ssh
cp ~/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Testar acesso (em outro terminal)
ssh deploy@YOUR_SERVER_IP
```

---

## 3. Segurança do Servidor

### 3.1 Configurar SSH Seguro

```bash
# Editar configuração SSH
sudo vim /etc/ssh/sshd_config
```

**Alterações recomendadas:**
```ini
# Desabilitar login como root
PermitRootLogin no

# Desabilitar autenticação por senha
PasswordAuthentication no

# Porta SSH (opcional, mas recomendado mudar)
Port 2222

# Permitir apenas usuário deploy
AllowUsers deploy
```

```bash
# Reiniciar SSH
sudo systemctl restart sshd

# IMPORTANTE: Testar conexão em outro terminal antes de fechar!
ssh -p 2222 deploy@YOUR_SERVER_IP
```

### 3.2 Configurar Firewall (UFW)

```bash
# Resetar regras
sudo ufw reset

# Política padrão: negar entrada, permitir saída
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH (use a porta que configurou)
sudo ufw allow 2222/tcp comment 'SSH'

# Permitir HTTP e HTTPS
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'

# Ativar firewall
sudo ufw enable

# Verificar status
sudo ufw status verbose
```

### 3.3 Configurar Fail2Ban

```bash
# Criar configuração local
sudo vim /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 5

[sshd]
enabled = true
port = 2222
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 24h
```

```bash
# Reiniciar fail2ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban

# Verificar status
sudo fail2ban-client status sshd
```

### 3.4 Configurar Atualizações Automáticas de Segurança

```bash
# Instalar unattended-upgrades
sudo apt install -y unattended-upgrades

# Configurar
sudo dpkg-reconfigure -plow unattended-upgrades
```

---

## 4. Instalação do Docker

### 4.1 Instalar Docker Engine

```bash
# Remover versões antigas
sudo apt remove docker docker-engine docker.io containerd runc 2>/dev/null

# Adicionar repositório oficial
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Adicionar usuário ao grupo docker
sudo usermod -aG docker deploy

# Aplicar mudança de grupo (ou faça logout/login)
newgrp docker

# Verificar instalação
docker --version
docker compose version
```

### 4.2 Configurar Docker para Produção

```bash
# Criar configuração do daemon
sudo vim /etc/docker/daemon.json
```

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "live-restore": true,
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 65536,
      "Soft": 65536
    }
  }
}
```

```bash
# Reiniciar Docker
sudo systemctl restart docker
sudo systemctl enable docker
```

---

## 5. Configuração do Projeto

### 5.1 Clonar Repositório

```bash
# Criar diretório de aplicações
sudo mkdir -p /opt/apps
sudo chown deploy:deploy /opt/apps
cd /opt/apps

# Clonar repositório (use HTTPS ou SSH)
git clone https://github.com/SEU_USUARIO/Tacto-System.git tactoflow
cd tactoflow
```

### 5.2 Configurar Variáveis de Ambiente

```bash
# Copiar exemplo de produção
cp .env.production.example .env

# Editar com valores reais
vim .env
```

**⚠️ IMPORTANTE: Gere valores seguros para:**

```bash
# Gerar SECRET_KEY segura
openssl rand -hex 32

# Gerar senha do banco
openssl rand -base64 24
```

**Exemplo de `.env` preenchido:**
```ini
# Application
APP_NAME=TactoFlow
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=sua_chave_gerada_aqui_com_openssl

# Database
DB_HOST=postgres
DB_PORT=5432
DB_USER=tacto
DB_PASSWORD=sua_senha_segura_aqui
DB_NAME=tacto_db
DB_ECHO=false
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Tacto API (preencher com dados reais)
TACTO_API_BASE_URL=https://api-externa.tactonuvem.com.br
TACTO_AUTH_URL=https://accounts.tactonuvem.com.br/connect/token
TACTO_CLIENT_ID=integracao-externa
TACTO_CLIENT_SECRET=SEU_CLIENT_SECRET
TACTO_CHAVE_ORIGEM=SUA_CHAVE_ORIGEM

# Join API (preencher com dados reais)
JOIN_API_BASE_URL=https://api-prd.joindeveloper.com.br
JOIN_TOKEN_CLIENTE=SEU_TOKEN_JOIN

# Google AI
GOOGLE_API_KEY=SUA_API_KEY_GOOGLE
LLM_MODEL=gemini-2.5-flash

# Attendant
ATTENDANT_NAME=Maria

# API Port
API_PORT=8000
```

### 5.3 Configurar Permissões

```bash
# Proteger arquivo .env
chmod 600 .env

# Criar diretórios necessários
mkdir -p nginx/ssl
mkdir -p logs
```

---

## 6. SSL/HTTPS com Let's Encrypt

### 6.1 Instalar Certbot

```bash
sudo apt install -y certbot
```

### 6.2 Obter Certificado (antes de subir o Nginx)

```bash
# Parar qualquer serviço na porta 80
sudo systemctl stop nginx 2>/dev/null || true

# Obter certificado standalone
sudo certbot certonly --standalone \
    -d seu-dominio.com.br \
    --email seu-email@exemplo.com \
    --agree-tos \
    --non-interactive
```

### 6.3 Copiar Certificados para o Projeto

```bash
# Copiar certificados
sudo cp /etc/letsencrypt/live/seu-dominio.com.br/fullchain.pem /opt/apps/tactoflow/nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/seu-dominio.com.br/privkey.pem /opt/apps/tactoflow/nginx/ssl/key.pem

# Ajustar permissões
sudo chown deploy:deploy /opt/apps/tactoflow/nginx/ssl/*.pem
chmod 600 /opt/apps/tactoflow/nginx/ssl/*.pem
```

### 6.4 Configurar Renovação Automática

```bash
# Criar script de renovação
sudo vim /opt/apps/tactoflow/scripts/renew-ssl.sh
```

```bash
#!/bin/bash
# Renovar certificado e copiar para o projeto

certbot renew --quiet

# Copiar novos certificados
cp /etc/letsencrypt/live/seu-dominio.com.br/fullchain.pem /opt/apps/tactoflow/nginx/ssl/cert.pem
cp /etc/letsencrypt/live/seu-dominio.com.br/privkey.pem /opt/apps/tactoflow/nginx/ssl/key.pem

# Recarregar nginx
docker exec tactoflow_nginx_prod nginx -s reload
```

```bash
# Tornar executável
sudo chmod +x /opt/apps/tactoflow/scripts/renew-ssl.sh

# Adicionar ao cron (rodar 2x por dia)
sudo crontab -e
```

```cron
0 3,15 * * * /opt/apps/tactoflow/scripts/renew-ssl.sh >> /var/log/ssl-renew.log 2>&1
```

---

## 7. Deploy da Aplicação

### 7.1 Build e Start

```bash
cd /opt/apps/tactoflow

# Build da imagem de produção
docker compose -f docker-compose.prod.yml build

# Subir serviços (sem nginx primeiro)
docker compose -f docker-compose.prod.yml up -d postgres redis api

# Aguardar serviços ficarem healthy
docker compose -f docker-compose.prod.yml ps

# Executar migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# Subir nginx (com SSL configurado)
docker compose -f docker-compose.prod.yml --profile with-nginx up -d nginx
```

### 7.2 Verificar Deploy

```bash
# Status dos containers
docker compose -f docker-compose.prod.yml ps

# Verificar logs
docker compose -f docker-compose.prod.yml logs -f api

# Testar health check
curl http://localhost:8000/health

# Testar HTTPS (substitua pelo seu domínio)
curl https://seu-dominio.com.br/health
```

### 7.3 Script de Deploy Rápido

Crie o script `/opt/apps/tactoflow/deploy.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Iniciando deploy..."

cd /opt/apps/tactoflow

# Pull latest code
echo "📥 Atualizando código..."
git pull origin main

# Build
echo "🔨 Building imagem..."
docker compose -f docker-compose.prod.yml build api

# Deploy com zero downtime
echo "🔄 Reiniciando API..."
docker compose -f docker-compose.prod.yml up -d --no-deps api

# Aguardar health check
echo "⏳ Aguardando health check..."
sleep 10

# Verificar
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✅ Deploy concluído com sucesso!"
else
    echo "❌ Health check falhou!"
    docker compose -f docker-compose.prod.yml logs --tail=50 api
    exit 1
fi
```

```bash
chmod +x /opt/apps/tactoflow/deploy.sh
```

---

## 8. Configuração de DNS

### 8.1 Registros DNS Necessários

Configure no seu provedor de DNS:

| Tipo | Nome | Valor | TTL |
|------|------|-------|-----|
| A | @ | IP_DO_SERVIDOR | 300 |
| A | www | IP_DO_SERVIDOR | 300 |
| A | api | IP_DO_SERVIDOR | 300 |

### 8.2 Verificar Propagação

```bash
# Verificar DNS
dig +short seu-dominio.com.br
nslookup seu-dominio.com.br
```

---

## 9. Monitoramento e Logs

### 9.1 Visualizar Logs

```bash
# Logs da API (tempo real)
docker compose -f docker-compose.prod.yml logs -f api

# Logs do PostgreSQL
docker compose -f docker-compose.prod.yml logs -f postgres

# Logs do Nginx
docker compose -f docker-compose.prod.yml logs -f nginx

# Todos os logs
docker compose -f docker-compose.prod.yml logs -f
```

### 9.2 Monitoramento com htop e docker stats

```bash
# Uso de recursos do sistema
htop

# Uso de recursos dos containers
docker stats
```

### 9.3 Script de Health Check

Crie `/opt/apps/tactoflow/scripts/healthcheck.sh`:

```bash
#!/bin/bash

API_URL="http://localhost:8000/health"
WEBHOOK_URL="https://hooks.slack.com/services/SEU_WEBHOOK"  # Opcional

check_health() {
    if curl -sf "$API_URL" > /dev/null; then
        echo "$(date): ✅ API está saudável"
        return 0
    else
        echo "$(date): ❌ API não está respondendo!"
        
        # Opcional: enviar alerta para Slack
        # curl -X POST -H 'Content-type: application/json' \
        #     --data '{"text":"🚨 TactoFlow API está down!"}' \
        #     "$WEBHOOK_URL"
        
        return 1
    fi
}

check_health
```

```bash
chmod +x /opt/apps/tactoflow/scripts/healthcheck.sh

# Adicionar ao cron (a cada 5 minutos)
crontab -e
```

```cron
*/5 * * * * /opt/apps/tactoflow/scripts/healthcheck.sh >> /opt/apps/tactoflow/logs/healthcheck.log 2>&1
```

---

## 10. Backup Automático

### 10.1 Script de Backup do PostgreSQL

Crie `/opt/apps/tactoflow/scripts/backup-db.sh`:

```bash
#!/bin/bash

# Configurações
BACKUP_DIR="/opt/apps/tactoflow/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Criar diretório se não existir
mkdir -p "$BACKUP_DIR"

# Nome do arquivo
BACKUP_FILE="$BACKUP_DIR/tacto_db_$DATE.sql.gz"

echo "$(date): Iniciando backup..."

# Executar backup
docker compose -f /opt/apps/tactoflow/docker-compose.prod.yml exec -T postgres \
    pg_dump -U tacto tacto_db | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "$(date): ✅ Backup criado: $BACKUP_FILE"
    
    # Tamanho do backup
    ls -lh "$BACKUP_FILE"
    
    # Limpar backups antigos
    find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "$(date): Backups com mais de $RETENTION_DAYS dias removidos"
else
    echo "$(date): ❌ Falha no backup!"
    exit 1
fi
```

```bash
chmod +x /opt/apps/tactoflow/scripts/backup-db.sh

# Criar diretório de backups
mkdir -p /opt/apps/tactoflow/backups

# Adicionar ao cron (diário às 3h)
crontab -e
```

```cron
0 3 * * * /opt/apps/tactoflow/scripts/backup-db.sh >> /opt/apps/tactoflow/logs/backup.log 2>&1
```

### 10.2 Backup para Storage Externo (Opcional)

Para backups offsite, configure o Hetzner Storage Box ou AWS S3:

```bash
# Instalar rclone
curl https://rclone.org/install.sh | sudo bash

# Configurar (seguir wizard)
rclone config

# Adicionar sync ao script de backup
rclone copy "$BACKUP_DIR" remote:tactoflow-backups/
```

---

## 11. CI/CD com GitHub Actions

### 11.1 Criar Workflow de Deploy

Crie `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          port: ${{ secrets.SERVER_PORT }}
          script: |
            cd /opt/apps/tactoflow
            ./deploy.sh
```

### 11.2 Configurar Secrets no GitHub

No repositório, vá em **Settings > Secrets and variables > Actions** e adicione:

| Secret | Valor |
|--------|-------|
| `SERVER_HOST` | IP do servidor |
| `SERVER_USER` | deploy |
| `SERVER_PORT` | 2222 |
| `SERVER_SSH_KEY` | Chave privada SSH |

### 11.3 Gerar Chave SSH para Deploy

```bash
# No servidor
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# Adicionar ao authorized_keys
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys

# Copiar chave privada para o GitHub Secrets
cat ~/.ssh/github_deploy
```

---

## 12. Manutenção e Troubleshooting

### 12.1 Comandos Úteis

```bash
# Reiniciar todos os serviços
docker compose -f docker-compose.prod.yml restart

# Reiniciar apenas a API
docker compose -f docker-compose.prod.yml restart api

# Ver uso de disco
df -h
docker system df

# Limpar recursos não utilizados
docker system prune -a --volumes

# Acessar shell do container
docker compose -f docker-compose.prod.yml exec api bash

# Acessar PostgreSQL
docker compose -f docker-compose.prod.yml exec postgres psql -U tacto tacto_db

# Acessar Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli
```

### 12.2 Problemas Comuns

#### API não inicia
```bash
# Ver logs detalhados
docker compose -f docker-compose.prod.yml logs api --tail=100

# Verificar variáveis de ambiente
docker compose -f docker-compose.prod.yml exec api env
```

#### Banco de dados não conecta
```bash
# Verificar se postgres está rodando
docker compose -f docker-compose.prod.yml ps postgres

# Testar conexão
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U tacto
```

#### Certificado SSL expirado
```bash
# Renovar manualmente
sudo certbot renew --force-renewal
/opt/apps/tactoflow/scripts/renew-ssl.sh
```

### 12.3 Rollback

```bash
# Ver commits recentes
git log --oneline -10

# Voltar para commit anterior
git checkout COMMIT_HASH

# Rebuild e deploy
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

---

## 13. Checklist Final

### Antes do Deploy
- [ ] Domínio configurado e propagado
- [ ] Certificado SSL obtido
- [ ] `.env` preenchido com valores de produção
- [ ] Chaves de API (Tacto, Join, Google) validadas
- [ ] Firewall configurado (UFW)
- [ ] Fail2ban ativo
- [ ] SSH hardened (sem root, sem senha)

### Após o Deploy
- [ ] Health check respondendo (`/health`)
- [ ] Webhook Join configurado com URL de produção
- [ ] Logs sendo gerados corretamente
- [ ] Backup automático configurado
- [ ] SSL funcionando (HTTPS)
- [ ] Testar fluxo completo (enviar mensagem WhatsApp)

### Monitoramento Contínuo
- [ ] Cron de health check ativo
- [ ] Cron de backup ativo
- [ ] Cron de renovação SSL ativo
- [ ] Alertas configurados (opcional)

---

## 📞 Suporte

Em caso de problemas:

1. Verifique os logs: `docker compose -f docker-compose.prod.yml logs -f`
2. Verifique o status: `docker compose -f docker-compose.prod.yml ps`
3. Consulte esta documentação
4. Abra uma issue no repositório

---

**Última atualização:** Março 2026
