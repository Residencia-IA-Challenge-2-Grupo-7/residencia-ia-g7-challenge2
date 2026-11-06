"""Cliente do LLM do interpretador: OpenRouter com saída estruturada e roteamento restrito (ADR 0007).

Trocar de provedor = outra classe com o mesmo método `interpretar(sistema, usuario) -> (dict, meta)` (RNF-12).
"""
import json
import time
from dataclasses import dataclass

import requests

from .config import CFG, segredo
from .esquema import schema_llm

L = CFG["llm"]


class ErroLLM(RuntimeError):
    pass


@dataclass
class Meta:
    modelo: str
    provedor: str | None
    latencia_s: float
    tokens_entrada: int | None
    tokens_saida: int | None
    custo_usd: float | None


class OpenRouter:
    def __init__(self, modelo: str | None = None):
        self.chave = segredo(L["chave_env"])
        if not self.chave:
            raise ErroLLM(f"Defina {L['chave_env']} no .env (fora do git) ou no ambiente.")
        self.modelos = [modelo] if modelo else [L["modelo"], *L.get("reservas", [])]
        self.sessao = requests.Session()

    def _corpo(self, modelo: str, sistema: str, usuario: str) -> dict:
        return {
            "model": modelo,
            "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
            "temperature": L["temperatura"],
            "max_tokens": L["max_tokens"],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "interpretacao", "strict": True, "schema": schema_llm()}},
            "provider": dict(L["roteamento"]),
            "reasoning": {"enabled": bool(L.get("raciocinio", False))},
            "usage": {"include": True},
        }

    def interpretar(self, sistema: str, usuario: str) -> tuple[dict, Meta]:
        erros = []
        for modelo in self.modelos:
            for _ in range(L["tentativas"]):
                t0 = time.perf_counter()
                try:
                    r = self.sessao.post(L["url"], json=self._corpo(modelo, sistema, usuario), timeout=L["timeout_s"],
                                         headers={"Authorization": f"Bearer {self.chave}",
                                                  "X-Title": "Orquestrador de Roles (Residencia IA UnB)"})
                    dt = time.perf_counter() - t0
                    if r.status_code >= 400:
                        erros.append(f"{modelo}: HTTP {r.status_code} {r.text[:300]}")
                        if r.status_code in (400, 401, 402, 403, 404):
                            break  # não adianta repetir com o mesmo modelo
                        continue
                    d = r.json()
                    if "error" in d:
                        erros.append(f"{modelo}: {d['error']}")
                        continue
                    escolha = d["choices"][0]
                    texto = escolha["message"].get("content")
                    if not texto:  # ex.: tokens esgotados antes do JSON (finish_reason = length)
                        erros.append(f"{modelo}: resposta vazia (finish_reason={escolha.get('finish_reason')})")
                        continue
                    u = d.get("usage") or {}
                    return json.loads(texto), Meta(d.get("model", modelo), d.get("provider"), dt,
                                                  u.get("prompt_tokens"), u.get("completion_tokens"), u.get("cost"))
                except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as e:
                    erros.append(f"{modelo}: {type(e).__name__}: {e}")
        raise ErroLLM("; ".join(erros[-4:]))
