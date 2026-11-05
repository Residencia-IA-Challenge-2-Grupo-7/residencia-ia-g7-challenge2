#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "Verificando bibliotecas (yt-dlp e curl_cffi)..."
python3 -m pip install -q -r requirements.txt
echo "Executando Coletor TikTok 2FA (2026) no Terminal..."
python3 coletor_tiktok_2fa.py 15
echo "Atualizando e Imprimindo o Banco de Dados Vetorial no Terminal..."
python3 banco_vetorial.py
