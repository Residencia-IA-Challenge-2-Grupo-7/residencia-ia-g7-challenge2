#!/usr/bin/env python3
"""Atualiza as issues da Semana 4 (#64 a #76) no GitHub via REST API,
adicionando o critério de aceitação de registro no docs/semanas/semana-04.md.

Uso:
    GITHUB_TOKEN=ghp_seu_token python scripts/atualizar_issues_semana4.py
"""
import os
import sys
import json
import ssl
import urllib.request
import urllib.error

# Cria contexto SSL seguro ou tolerante a certificados locais do macOS
try:
    import certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
except Exception:
    ctx = ssl._create_unverified_context()

REPO = "Residencia-IA-Challenge-2-Grupo-7/residencia-ia-g7-challenge2"
ISSUES_SEMANA_4 = list(range(64, 77))  # #64 até #76

ITEM_CHECKLIST = (
    "- [ ] Registrar na Seção 8 de `docs/semanas/semana-04.md` o que foi implementado, "
    "justificando as decisões técnicas de arquitetura, arquivos criados e testes com evidências."
)

def atualizar_issue(token: str, issue_num: int):
    url = f"https://api.github.com/repos/{REPO}/issues/{issue_num}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Desafio-Multiagente-Semana4",
    }

    # 1. Obter a descrição atual da issue
    req_get = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req_get, context=ctx) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"❌ Erro ao buscar issue #{issue_num}: HTTP {e.code} - {e.reason}")
        return False

    body_atual = data.get("body") or ""

    if "docs/semanas/semana-04.md" in body_atual:
        print(f"ℹ️ Issue #{issue_num} já possui o critério de documentação. Pulando...")
        return True

    # 2. Inserir o critério no checklist existente ou ao final
    if "Checklist de Implementação" in body_atual:
        partes = body_atual.split("Checklist de Implementação")
        # Se houver cabeçalho de checklist, anexa logo abaixo
        novo_body = partes[0] + "Checklist de Implementação\n" + f"{ITEM_CHECKLIST}" + partes[1]
    elif "### Checklist" in body_atual or "## Checklist" in body_atual:
        marcador = "### Checklist" if "### Checklist" in body_atual else "## Checklist"
        partes = body_atual.split(marcador)
        novo_body = partes[0] + marcador + f"\n{ITEM_CHECKLIST}" + partes[1]
    else:
        novo_body = body_atual.strip() + f"\n\n### Critérios de Aceitação Obrigatórios\n{ITEM_CHECKLIST}\n"

    # 3. Atualizar a issue via PATCH
    payload = json.dumps({"body": novo_body}).encode("utf-8")
    req_patch = urllib.request.Request(url, data=payload, headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req_patch, context=ctx) as resp:
            print(f"✅ Issue #{issue_num} atualizada com sucesso!")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ Erro ao atualizar issue #{issue_num}: HTTP {e.code} - {e.reason}")
        return False

def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("❌ Erro: Variável GITHUB_TOKEN não encontrada no ambiente.")
        print("Execute com seu token pessoal do GitHub (Personal Access Token):")
        print("    GITHUB_TOKEN=ghp_... python scripts/atualizar_issues_semana4.py")
        sys.exit(1)

    print(f"🚀 Iniciando atualização das issues {ISSUES_SEMANA_4[0]} a {ISSUES_SEMANA_4[-1]} no repositório {REPO}...")
    sucesso = 0
    for num in ISSUES_SEMANA_4:
        if atualizar_issue(token, num):
            sucesso += 1

    print(f"\n🎉 Concluído: {sucesso}/{len(ISSUES_SEMANA_4)} issues atualizadas.")

if __name__ == "__main__":
    main()
