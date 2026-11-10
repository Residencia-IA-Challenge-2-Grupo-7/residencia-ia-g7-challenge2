# ==============================================================================
# MAKEFILE - ATALHOS RÁPIDOS MULTIPLATAFORMA (DevOps Grupo 7)
# ==============================================================================
# Ajuda os desenvolvedores a rodar testes, containers e infraestrutura
# sem precisar decorar comandos longos do Docker.

.PHONY: help up down test test-local logs clean

help:
	@echo "====================================================================="
	@echo "Orquestrador de Rolês - Comandos Rápidos da Equipe"
	@echo "====================================================================="
	@echo "  make test        - Executa a suíte de testes completa DENTRO do Docker"
	@echo "  make test-local  - Executa os testes no ambiente local (venv)"
	@echo "  make up          - Sobe todos os containers em segundo plano (Postgres + App)"
	@echo "  make down        - Para todos os containers do Docker"
	@echo "  make logs        - Exibe os logs dos containers em tempo real"
	@echo "  make clean       - Limpa caches e arquivos temporários do Python"
	@echo "====================================================================="

# Detecta automaticamente o pytest do venv caso não esteja no PATH
VENV_PYTEST := $(shell which pytest 2>/dev/null || echo ./.venv/bin/pytest)

# Executa testes dentro do container Docker oficial
test:
	docker compose run --rm app pytest -v tests/test_smoke.py tests/test_logger_e_cache.py tests/test_db_schema.py tests/test_fluxo_completo_dois_amigos.py tests/test_interpretador.py

# Executa testes direto na máquina local (detecta venv automaticamente)
test-local:
	PYTHONPATH=. $(VENV_PYTEST) -v tests/test_smoke.py tests/test_logger_e_cache.py tests/test_db_schema.py tests/test_fluxo_completo_dois_amigos.py tests/test_interpretador.py

# Sobe os containers (Postgres com pgvector e App)
up:
	docker compose up -d

# Para todos os serviços
down:
	docker compose down

# Acompanha logs dos containers
logs:
	docker compose logs -f

# Limpa caches locais
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
