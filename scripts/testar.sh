#!/usr/bin/env bash
# ==============================================================================
# Atalho de Testes para macOS e Linux (Grupo 7)
# ==============================================================================
set -e

echo "🐳 Executando testes automatizados dentro do container Docker..."
docker compose run --rm app pytest -v "$@"
