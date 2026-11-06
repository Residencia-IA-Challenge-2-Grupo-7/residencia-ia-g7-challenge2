#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo " Instalação Oficial do Docker Engine no Zorin OS 18 / Ubuntu Noble"
echo "=========================================================="

if [ "$EUID" -ne 0 ]; then
  echo "[-] Erro: Este script precisa de privilégios de superusuário."
  echo "    Execute com: sudo bash $0"
  exit 1
fi

TARGET_USER="${SUDO_USER:-$USER}"

echo "[+] 1. Atualizando índices do APT e instalando pré-requisitos..."
apt-get update -y
apt-get install -y ca-certificates curl gnupg

echo "[+] 2. Configurando o chaveiro seguro GPG oficial do Docker..."
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "[+] 3. Adicionando o repositório oficial do Docker (Ubuntu Noble)..."
ARCH="$(dpkg --print-architecture)"
# Zorin OS 18 é baseado no Ubuntu 24.04 (noble)
UBUNTU_RELEASE="noble"

echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_RELEASE} stable" \
  > /etc/apt/sources.list.d/docker.list

echo "[+] 4. Instalando Docker Engine, Docker CLI, Containerd e Docker Compose..."
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "[+] 5. Ativando e iniciando o serviço do Docker..."
systemctl enable --now docker

echo "[+] 6. Adicionando o usuário '${TARGET_USER}' ao grupo 'docker'..."
usermod -aG docker "${TARGET_USER}"

echo ""
echo "=========================================================="
echo " Docker instalado e configurado com sucesso!"
docker --version
docker compose version
echo "=========================================================="
echo ""
echo "DICA: Para usar o Docker sem 'sudo' na sua sessão atual, execute:"
echo "    newgrp docker"
echo ""
