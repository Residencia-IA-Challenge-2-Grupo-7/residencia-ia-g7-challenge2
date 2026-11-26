#!/usr/bin/env bash
# Publica o mapa no site (repositório público residencia-ia-g7-arquitetura, servido pelo GitHub Pages).
# Uso: bash docs/arquitetura/publicar.sh "o que mudou"
# Precisa do gh autenticado com acesso de escrita à organização.
set -euo pipefail
dir="$(cd "$(dirname "$0")" && pwd)"
node "$dir/checar.mjs"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
gh repo clone Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-arquitetura "$tmp" -- -q
cp "$dir/index.html" "$tmp/index.html"
cd "$tmp"
if git diff --quiet; then echo "O site já está igual ao index.html daqui."; exit 0; fi
git add index.html
git commit -q -m "docs: atualiza o mapa da arquitetura" -m "${1:-}"
git push -q
echo "Publicado; o GitHub Pages leva cerca de 1 minuto para atualizar:"
echo "https://residencia-ia-challenge-2-grupo-7.github.io/residencia-ia-g7-arquitetura/"
