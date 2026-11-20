"""Teste da demonstração da semana 4 (issue #74): roda o script sem LLM nos dois cenários da #66 e confere o que o
relatório (#76) usa — o resumo, o veredito de cada cenário e a varredura de vazamento."""
import subprocess
import sys
from pathlib import Path


def test_demo_offline_roda_os_dois_cenarios_e_grava_o_log(tmp_path):
    log, diagrama = tmp_path / "log.txt", tmp_path / "grafo.mmd"
    r = subprocess.run([sys.executable, "scripts/demo_multiagente.py", "--offline", "--saida", str(log),
                        "--diagrama", str(diagrama)], capture_output=True, text=True, encoding="utf-8",
                       timeout=300, env={**__import__("os").environ, "PYTHONPATH": "."})
    assert r.returncode == 0, r.stderr[-2000:]
    texto = log.read_text(encoding="utf-8")
    for trecho in ("ATO 1 — MEMÓRIA", "CENÁRIO ROLE-PADR", "CENÁRIO ROLE-CTRL", "RESUMO DOS CENÁRIOS"):
        assert trecho in texto, trecho
    padrao = texto.split("CENÁRIO ROLE-PADR")[1].split("CENÁRIO ROLE-CTRL")[0]
    assert "sem cartões para votar" in padrao
    controle = texto.split("CENÁRIO ROLE-CTRL")[1].split("RESUMO DOS CENÁRIOS")[0]
    assert "Cartões fora dos viáveis: nenhum" in controle
    assert texto.count("Nomes de membros encontrados: nenhum") == 2
    assert "no_validacao" in diagrama.read_text(encoding="utf-8")
