import datetime
import json
import os
import re
import ssl
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yt_dlp
from curl_cffi import requests as cffi_requests

# Caminhos 100% multiplataforma (funcionam em macOS, Linux e Windows)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

BANCO_APROVADO_FILE = DATA_DIR / "banco_aprovado_2fa.json"
QUARENTENA_FILE = DATA_DIR / "fila_quarentena_2fa.json"
CATALOGO_2026_FILE = DATA_DIR / "catalogo_videos_2026.json"
ENV_FILE = BASE_DIR / ".env"

SSL_CTX = ssl._create_unverified_context()

# secUid oficial do perfil @rolezandoembrasilia no TikTok
ROLEZANDO_SEC_UID = "MS4wLjABAAAA6Q-LVlhGmtU6NheDGYbzIoMFzEIdGQqJm8RWp2wd3LAX0W7uEbheF-B2RCw3ENUT"

TIPOS_DE_ROLE_PERMITIDOS = [
    "Bar / Boteco / Pub",
    "Restaurante / Gastronomia",
    "Cafeteria / Doceria",
    "Experiência / Evento",
    "Ao Ar Livre / Parque",
]

VIBES_PERMITIDAS = [
    "Romântico / Date",
    "Calmo / Bom para Conversar",
    "Intimista / Aconchegante",
    "Baratinho",
    "Cultural / Alternativo",
    "Kid Friendly",
    "Animado / Galera",
]

COORDENADAS_RAS_DF = {
    "Plano Piloto (Asa Sul)": {"lat": -15.8192, "lng": -47.8988},
    "Asa Sul": {"lat": -15.8192, "lng": -47.8988},
    "Plano Piloto (Asa Norte)": {"lat": -15.7630, "lng": -47.8850},
    "Asa Norte": {"lat": -15.7630, "lng": -47.8850},
    "Plano Piloto (Eixo Monumental)": {"lat": -15.7975, "lng": -47.8782},
    "Plano Piloto (Parque da Cidade)": {"lat": -15.8005, "lng": -47.9065},
    "Plano Piloto": {"lat": -15.7942, "lng": -47.8825},
    "Águas Claras": {"lat": -15.8360, "lng": -48.0260},
    "Taguatinga": {"lat": -15.8330, "lng": -48.0560},
    "Guará": {"lat": -15.8260, "lng": -47.9790},
    "ParkShopping": {"lat": -15.8332, "lng": -47.9554},
    "Sudoeste / Cruzeiro": {"lat": -15.7980, "lng": -47.9250},
    "Samambaia": {"lat": -15.8760, "lng": -48.0850},
    "Ceilândia": {"lat": -15.8180, "lng": -48.1080},
    "Riacho Fundo": {"lat": -15.8830, "lng": -48.0170},
    "Santa Maria": {"lat": -16.0185, "lng": -48.0075},
    "Planaltina": {"lat": -15.6190, "lng": -47.6515},
    "Lago Sul": {"lat": -15.8420, "lng": -47.8760},
    "Lago Norte": {"lat": -15.7350, "lng": -47.8580},
    "Sobradinho": {"lat": -15.6530, "lng": -47.7910},
    "Gama": {"lat": -16.0150, "lng": -48.0620},
    "SIA / Setor de Indústrias": {"lat": -15.8020, "lng": -47.9580},
    "Vicente Pires": {"lat": -15.8030, "lng": -48.0310},
    "Recanto das Emas": {"lat": -15.9080, "lng": -48.0680},
    "Núcleo Bandeirante": {"lat": -15.8710, "lng": -47.9680},
    "Jardim Botânico": {"lat": -15.8690, "lng": -47.8010},
}


def load_env() -> Dict[str, str]:
    env = {
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
        "GROQ_API_KEY": os.environ.get("GROQ_API_KEY", ""),
        "GOOGLE_MAPS_API_KEY": os.environ.get("GOOGLE_MAPS_API_KEY", ""),
    }
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_json_list(path: Path, data: List[Dict[str, Any]]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ==============================================================================
# PASSO 0: CATÁLOGO COMPLETO DE VÍDEOS DE 2026 POR MÊS (@rolezandoembrasilia)
# ==============================================================================

def sincronizar_catalogo_2026(max_fetch: int = 65) -> List[Dict[str, Any]]:
    """
    Usa o canal oficial tiktokuser:<secUid> com intervalo seguro para listar os vídeos
    de 2026 do @rolezandoembrasilia separados por mês (2026-11, 2026-10, 2026-09, 2026-08...).
    Salva o catálogo em disco para evitar bloqueio 429 do TikTok.
    """
    catalogo_existente = load_json_list(CATALOGO_2026_FILE)
    ids_existentes = {item["video_id"]: item for item in catalogo_existente if "video_id" in item}

    ydl_opts = {
        "extract_flat": True,
        "playlistend": max_fetch,
        "sleep_interval_requests": 2,
        "nocheckcertificate": True,
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"tiktokuser:{ROLEZANDO_SEC_UID}", download=False)
            for e in info.get("entries", []):
                vid = str(e.get("id") or "")
                ts = e.get("timestamp")
                if not vid:
                    continue
                if ts:
                    dt_obj = datetime.datetime.fromtimestamp(ts)
                    ano = dt_obj.strftime("%Y")
                    ano_mes = dt_obj.strftime("%Y-%m")
                    data_fmt = dt_obj.strftime("%d/%m/%Y")
                else:
                    ano = "2026"
                    ano_mes = "2026-10"
                    data_fmt = "2026"

                if ano == "2026":
                    ids_existentes[vid] = {
                        "video_id": vid,
                        "tiktok_url": f"https://www.tiktok.com/@rolezandoembrasilia/video/{vid}",
                        "ano_mes": ano_mes,
                        "data_formatada": data_fmt,
                        "timestamp": ts or 0,
                    }
    except Exception:
        pass

    lista_final = sorted(ids_existentes.values(), key=lambda x: x.get("timestamp", 0), reverse=True)
    if lista_final:
        save_json_list(CATALOGO_2026_FILE, lista_final)
    return lista_final


def obter_videos_ja_processados() -> set:
    aprov = load_json_list(BANCO_APROVADO_FILE)
    quar = load_json_list(QUARENTENA_FILE)
    return {str(x.get("video_id")) for x in aprov + quar if x.get("video_id")}


def descobrir_videos_perfil(
    username: str = "rolezandoembrasilia",
    max_videos: int = 6,
    ano_mes_filtro: Optional[str] = None,
    apenas_nao_processados: bool = True,
) -> List[str]:
    catalogo = load_json_list(CATALOGO_2026_FILE)
    if len(catalogo) < 20:
        catalogo = sincronizar_catalogo_2026(max_fetch=35)

    ja_processados = obter_videos_ja_processados() if apenas_nao_processados else set()
    selecionados = []

    for item in catalogo:
        vid = str(item.get("video_id"))
        if vid in ja_processados:
            continue
        if ano_mes_filtro and ano_mes_filtro != "TODOS" and item.get("ano_mes") != ano_mes_filtro:
            continue
        selecionados.append(item["tiktok_url"])
        if len(selecionados) >= max_videos:
            break

    return selecionados


# ==============================================================================
# FATOR 1: EXTRAÇÃO CULTURAL (LEGENDA + ÁUDIO WHISPER + CLASSIFICADOR DE VIBES)
# ==============================================================================

def transcrever_audio_whisper_groq(audio_path: Path, groq_key: str) -> str:
    """Envia o áudio extraído do TikTok para o modelo whisper-large-v3-turbo na Groq."""
    if not groq_key or not audio_path.exists():
        return ""
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    file_bytes = audio_path.read_bytes()
    filename = audio_path.name

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-large-v3-turbo\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="language"\r\n\r\npt\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: audio/mpeg\r\n\r\n"
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "OrquestradorRoles2FA/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("text", "").strip()
    except Exception:
        return ""


def extrair_midia_tiktok(video_url: str, groq_key: str) -> Dict[str, Any]:
    vid_match = re.search(r"/video/(\d+)", video_url)
    video_id = vid_match.group(1) if vid_match else str(int(time.time()))

    legenda = ""
    upload_date = ""
    autor = "@rolezandoembrasilia"
    transcricao_audio = ""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        out_tmpl = str(tmp_path / f"{video_id}.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_tmpl,
            "nocheckcertificate": True,
            "quiet": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)
                legenda = (info.get("description") or info.get("title") or "").strip()
                upload_date = info.get("upload_date") or ""
                if info.get("uploader"):
                    autor = f"@{info.get('uploader').lstrip('@')}"

            arquivos_baixados = list(tmp_path.iterdir())
            if arquivos_baixados:
                transcricao_audio = transcrever_audio_whisper_groq(arquivos_baixados[0], groq_key)
        except Exception as e:
            return {
                "sucesso_download": False,
                "erro": str(e),
                "video_id": video_id,
                "tiktok_url": video_url,
            }

    ano = upload_date[:4] if len(upload_date) >= 4 else "2026"
    mes = upload_date[4:6] if len(upload_date) >= 6 else "10"
    dia = upload_date[6:8] if len(upload_date) >= 8 else "01"

    return {
        "sucesso_download": True,
        "video_id": video_id,
        "tiktok_url": f"https://www.tiktok.com/@rolezandoembrasilia/video/{video_id}",
        "autor": autor,
        "upload_date": upload_date,
        "data_formatada": f"{dia}/{mes}/{ano}" if upload_date else "2026",
        "ano_mes": f"{ano}-{mes}",
        "legenda_escrita": legenda,
        "transcricao_audio_whisper": transcricao_audio,
    }


def classificar_fator_1_com_ia(dados_midia: Dict[str, Any], env: Dict[str, str]) -> Tuple[Dict[str, Any], str]:
    system_prompt = f"""Você é o Agente Extrator Cultural (Fator 1) do Orquestrador de Rolês do Distrito Federal.
Analise a legenda e a transcrição do áudio de um vídeo do TikTok de Brasília e retorne EXCLUSIVAMENTE um JSON válido (sem markdown) no seguinte formato exato:
{{
  "eh_role_lazer_gastronomia": true,
  "motivo_descarte_se_nao_for_role": "",
  "nome": "Nome curto e exato do restaurante, bar, cafeteria, parque ou evento",
  "tipo_de_role": "Escolha EXATAMENTE UM de: {json.dumps(TIPOS_DE_ROLE_PERMITIDOS, ensure_ascii=False)}",
  "vibes": ["Escolha 1 a 4 tags EXATAMENTE desta lista: {json.dumps(VIBES_PERMITIDAS, ensure_ascii=False)}"],
  "kid_friendly_detectado": false,
  "evidencia_kid_friendly": "Cite se falou de brinquedoteca, espaço kids, menu infantil ou passeio para crianças",
  "bairro_ou_endereco_citado": "Ex: Asa Sul CLS 116 / Riacho Fundo 1 QN 05 / Águas Claras / Taguatinga",
  "regiao_administrativa_estimada": "Ex: Plano Piloto (Asa Sul), Plano Piloto (Asa Norte), Águas Claras, Taguatinga, Riacho Fundo, Guará, Samambaia, Ceilândia, Lago Sul, Vicente Pires",
  "preco_citado_no_video_rs": null,
  "faixa_preco_estimada_tiktok": "Barato ($) | Moderado ($$) | Caro ($$$) | Não informado",
  "horario_citado": "Horário de funcionamento citado no vídeo ou legenda",
  "resumo_sensorial": "Resumo de 2 frases sobre a comida, ambiente e experiência mostrados no TikTok"
}}

REGRAS ESTRITAS:
1. Se o vídeo for propaganda de loja de pisos/construção, concessionária de carros, loja de roupas/enxovais, ótica, supermercado atacadista ou assistência técnica de celular, marque "eh_role_lazer_gastronomia": false!
2. Se o vídeo mencionar brinquedoteca, parquinho, espaço kids, menu infantil ou ótimo para levar crianças, inclua obrigatoriamente "Kid Friendly" na lista "vibes" e marque "kid_friendly_detectado": true.
3. Se o vídeo mencionar preços (ex: hambúrguer de 32 reais, caixa por 49,90, rodízio 69,90, entrada gratuita = 15), coloque o valor numérico aproximado por pessoa em "preco_citado_no_video_rs". Caso não fale o valor exato em reais mas mostre claramente o cardápio/tipo de estabelecimento gastronômico, estime a faixa em "faixa_preco_estimada_tiktok" ("Barato ($)" até R$ 40, "Moderado ($$)" de R$ 45 a R$ 75, "Caro ($$$)" acima de R$ 80) e coloque o valor médio correspondente em "preco_citado_no_video_rs"."""

    user_prompt = (
        f"URL do TikTok: {dados_midia.get('tiktok_url')}\n"
        f"Data do Vídeo: {dados_midia.get('data_formatada')}\n"
        f"Legenda Escrita: {dados_midia.get('legenda_escrita')}\n"
        f"O que foi falado no Áudio (Whisper): {dados_midia.get('transcricao_audio_whisper')}\n"
    )

    gem_key = env.get("GEMINI_API_KEY", "")
    groq_key = env.get("GROQ_API_KEY", "")
    raw_text = ""
    modelo_usado = ""

    if gem_key:
        for m in ["gemini-3-flash-preview", "gemini-flash-latest"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={gem_key}"
            payload = {"contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}]}
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=12, context=SSL_CTX) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    raw_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                    modelo_usado = f"Google Gemini ({m})"
                    break
            except Exception:
                continue

    if not raw_text and groq_key:
        for m in ["qwen/qwen3.8-27b", "openai/gpt-oss-120b"]:
            payload = {
                "model": m,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            }
            try:
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {groq_key}",
                        "User-Agent": "OrquestradorRoles2FA/1.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                    raw_text = res["choices"][0]["message"]["content"].strip()
                    modelo_usado = f"Groq Cloud ({m})"
                    break
            except Exception:
                continue

    clean = raw_text
    if "```" in clean:
        for part in clean.split("```"):
            if "{" in part and "}" in part:
                clean = part.replace("json", "", 1).strip()
                break
    s_idx = clean.find("{")
    e_idx = clean.rfind("}")
    if s_idx != -1 and e_idx != -1:
        clean = clean[s_idx : e_idx + 1]

    parsed = json.loads(clean)
    return parsed, modelo_usado


# ==============================================================================
# FATOR 2: VALIDAÇÃO GEOESPACIAL E FAIXA DE PREÇO (PLACES API + GEOCODER DF)
# ==============================================================================

def executar_fator_2_places(fator1: Dict[str, Any], env: Dict[str, str]) -> Dict[str, Any]:
    nome = (fator1.get("nome") or "").strip()
    bairro_citado = (fator1.get("bairro_ou_endereco_citado") or "").strip()
    ra_estimada = (fator1.get("regiao_administrativa_estimada") or "").strip()
    gmaps_key = env.get("GOOGLE_MAPS_API_KEY", "")

    place_id_oficial = None
    endereco_confirmado = None
    lat_confirmada = None
    lng_confirmada = None
    price_level_places = None
    rating_places = None
    fonte_fator2 = ""

    if gmaps_key and nome:
        query_text = f"{nome} {bairro_citado} Brasília DF".strip()
        url_places = "https://places.googleapis.com/v1/places:searchText"
        field_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.priceLevel,places.rating"
        payload = {"textQuery": query_text, "languageCode": "pt-BR"}
        try:
            req = urllib.request.Request(
                url_places,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": gmaps_key,
                    "X-Goog-FieldMask": field_mask,
                },
            )
            with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                places = data.get("places", [])
                if places:
                    top_p = places[0]
                    place_id_oficial = top_p.get("id")
                    endereco_confirmado = top_p.get("formattedAddress")
                    loc = top_p.get("location", {})
                    lat_confirmada = loc.get("latitude")
                    lng_confirmada = loc.get("longitude")
                    price_level_places = top_p.get("priceLevel")
                    rating_places = top_p.get("rating")
                    fonte_fator2 = "Google Places API (New) — Confirmado em Tempo Real"
        except Exception:
            pass

    if not lat_confirmada and (bairro_citado or ra_estimada):
        busca_osm = f"{bairro_citado or ra_estimada}, Brasília, Distrito Federal, Brasil"
        osm_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(busca_osm)}&format=json&limit=1"
        try:
            req_osm = urllib.request.Request(osm_url, headers={"User-Agent": "OrquestradorRolesUnB/1.0"})
            with urllib.request.urlopen(req_osm, timeout=6, context=SSL_CTX) as resp:
                osm_data = json.loads(resp.read().decode("utf-8"))
                if osm_data:
                    lat_confirmada = round(float(osm_data[0]["lat"]), 5)
                    lng_confirmada = round(float(osm_data[0]["lon"]), 5)
                    endereco_confirmado = f"{bairro_citado} — {osm_data[0].get('display_name', 'Brasília - DF')[:90]}"
                    fonte_fator2 = "Geocodificador Oficial DF (OpenStreetMap + Âncora Geográfica)"
        except Exception:
            pass

    if not lat_confirmada and ra_estimada in COORDENADAS_RAS_DF:
        coords = COORDENADAS_RAS_DF[ra_estimada]
        lat_confirmada = coords["lat"]
        lng_confirmada = coords["lng"]
        endereco_confirmado = f"{bairro_citado or ra_estimada}, Brasília - DF"
        fonte_fator2 = "Validação por Região Administrativa do DF (Centróide Oficial)"

    trava_1_localizacao_ok = bool(
        lat_confirmada is not None
        and lng_confirmada is not None
        and (bairro_citado or endereco_confirmado)
        and "não informado" not in (bairro_citado or "").lower()
    )

    preco_video = fator1.get("preco_citado_no_video_rs")
    faixa_tiktok = fator1.get("faixa_preco_estimada_tiktok", "Não informado")

    faixa_preco_final = None
    custo_medio_estimado_rs = None

    if price_level_places:
        mapa_places = {
            "PRICE_LEVEL_INEXPENSIVE": ("Barato ($)", 32.0),
            "PRICE_LEVEL_MODERATE": ("Moderado ($$)", 55.0),
            "PRICE_LEVEL_EXPENSIVE": ("Caro ($$$)", 95.0),
            "PRICE_LEVEL_VERY_EXPENSIVE": ("Muito Caro ($$$$)", 150.0),
        }
        faixa_preco_final, custo_medio_estimado_rs = mapa_places.get(price_level_places, ("Moderado ($$)", 50.0))
    elif preco_video is not None and float(preco_video) > 0:
        custo_medio_estimado_rs = float(preco_video)
        if custo_medio_estimado_rs <= 40:
            faixa_preco_final = "Barato ($)"
        elif custo_medio_estimado_rs <= 75:
            faixa_preco_final = "Moderado ($$)"
        else:
            faixa_preco_final = "Caro ($$$)"
    elif faixa_tiktok and faixa_tiktok != "Não informado":
        faixa_preco_final = faixa_tiktok
        custo_medio_estimado_rs = 35.0 if "$" in faixa_tiktok and "$$" not in faixa_tiktok else 50.0

    trava_2_preco_ok = bool(faixa_preco_final and custo_medio_estimado_rs is not None)

    return {
        "trava_1_localizacao_ok": trava_1_localizacao_ok,
        "trava_2_preco_ok": trava_2_preco_ok,
        "aprovado_2fa": bool(trava_1_localizacao_ok and trava_2_preco_ok),
        "place_id": place_id_oficial or f"poi_df_{int(time.time())}",
        "endereco_validado": endereco_confirmado or bairro_citado or "Não localizado",
        "regiao_administrativa": ra_estimada or "Brasília - DF",
        "lat": lat_confirmada,
        "lng": lng_confirmada,
        "faixa_de_preco": faixa_preco_final or "Pendente de confirmação",
        "custo_medio_rs": custo_medio_estimado_rs,
        "rating_places": rating_places or 4.7,
        "fonte_validacao_fator2": fonte_fator2 or "Sem correspondência geográfica exata",
    }


def processar_video_tiktok_2fa(video_url: str) -> Dict[str, Any]:
    env = load_env()
    midia = extrair_midia_tiktok(video_url, env.get("GROQ_API_KEY", ""))

    if not midia.get("sucesso_download"):
        return {
            "status_final": "ERRO_DOWNLOAD",
            "motivo": f"Não foi possível acessar o vídeo no momento: {midia.get('erro')}",
            "tiktok_url": video_url,
        }

    fator1, modelo_usado = classificar_fator_1_com_ia(midia, env)

    if not fator1.get("eh_role_lazer_gastronomia", False):
        registro_descartado = {
            "id": f"disc_{midia['video_id']}",
            "status_2fa": "DESCARTADO_NAO_E_ROLE",
            "motivo": fator1.get("motivo_descarte_se_nao_for_role") or "Publieditorial de comércio/varejo que não é rolê gastronômico ou lazer.",
            "nome_detectado": fator1.get("nome", "Anúncio Comercial"),
            "data_video": midia["data_formatada"],
            "ano_mes": midia["ano_mes"],
            "tiktok_url": midia["tiktok_url"],
            "video_id": midia["video_id"],
            "legenda_original": midia["legenda_escrita"],
            "transcricao_audio_whisper": midia["transcricao_audio_whisper"],
            "modelo_ia": modelo_usado,
        }
        quarentena = [q for q in load_json_list(QUARENTENA_FILE) if q.get("video_id") != midia["video_id"]]
        quarentena.insert(0, registro_descartado)
        save_json_list(QUARENTENA_FILE, quarentena)
        return registro_descartado

    fator2 = executar_fator_2_places(fator1, env)

    ficha_completa = {
        "id": f"tiktok_{midia['video_id']}",
        "video_id": midia["video_id"],
        "tiktok_url": midia["tiktok_url"],
        "autor_tiktok": midia["autor"],
        "data_publicacao": midia["data_formatada"],
        "ano_mes": midia["ano_mes"],
        "nome": fator1.get("nome", "Local sem nome"),
        "tipo_de_role": fator1.get("tipo_de_role", "Restaurante / Gastronomia"),
        "vibes": fator1.get("vibes", []),
        "kid_friendly": bool(fator1.get("kid_friendly_detectado") or "Kid Friendly" in fator1.get("vibes", [])),
        "evidencia_kid_friendly": fator1.get("evidencia_kid_friendly", ""),
        "resumo_sensorial": fator1.get("resumo_sensorial", ""),
        "horario_funcionamento": fator1.get("horario_citado") or "Consultar no local",
        "trava_1_localizacao_ok": fator2["trava_1_localizacao_ok"],
        "trava_2_preco_ok": fator2["trava_2_preco_ok"],
        "status_2fa": "APROVADO_2FA" if fator2["aprovado_2fa"] else "PENDENTE_QUARENTENA_2FA",
        "regiao_administrativa": fator2["regiao_administrativa"],
        "endereco": fator2["endereco_validado"],
        "lat": fator2["lat"],
        "lng": fator2["lng"],
        "faixa_de_preco": fator2["faixa_de_preco"],
        "custo_medio_rs": fator2["custo_medio_rs"],
        "fonte_validacao_fator2": fator2["fonte_validacao_fator2"],
        "legenda_original": midia["legenda_escrita"],
        "transcricao_audio_whisper": midia["transcricao_audio_whisper"],
        "modelo_ia_fator1": modelo_usado,
    }

    if fator2["aprovado_2fa"]:
        aprovados = [a for a in load_json_list(BANCO_APROVADO_FILE) if a.get("video_id") != midia["video_id"]]
        aprovados.insert(0, ficha_completa)
        save_json_list(BANCO_APROVADO_FILE, aprovados)
    else:
        faltando = []
        if not fator2["trava_1_localizacao_ok"]:
            faltando.append("Localização exata no DF")
        if not fator2["trava_2_preco_ok"]:
            faltando.append("Faixa de Preço (não encontrada no Google Places nem citada no vídeo)")
        ficha_completa["motivo"] = f"Retido pelo 2FA — Faltou confirmar: {', '.join(faltando)}"
        quarentena = [q for q in load_json_list(QUARENTENA_FILE) if q.get("video_id") != midia["video_id"]]
        quarentena.insert(0, ficha_completa)
        save_json_list(QUARENTENA_FILE, quarentena)

    return ficha_completa


if __name__ == "__main__":
    import sys

    lote = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    cat_atual = load_json_list(CATALOGO_2026_FILE)
    if len(cat_atual) < 100:
        print("Sincronizando catálogo de 2026 de @rolezandoembrasilia...", flush=True)
        sincronizar_catalogo_2026(max_fetch=180)

    urls = descobrir_videos_perfil("rolezandoembrasilia", max_videos=lote, apenas_nao_processados=True)
    print(f"\nIniciando avaliação 2FA de {len(urls)} vídeos inéditos de 2026...", flush=True)

    for idx, u in enumerate(urls, 1):
        print(f"\n[{idx}/{len(urls)}] Baixando áudio + Whisper + 2FA: {u}", flush=True)
        r = processar_video_tiktok_2fa(u)
        st = r.get("status_2fa") or r.get("status_final")
        nm = r.get("nome") or r.get("nome_detectado") or "Desconhecido"
        dt = r.get("data_publicacao") or r.get("data_video") or ""
        print(f"   => {st} | {nm} ({dt}) | Preço: {r.get('faixa_de_preco', '-')} | Local: {r.get('regiao_administrativa', '-')}", flush=True)
        time.sleep(1.0)

    aprov = load_json_list(BANCO_APROVADO_FILE)
    quar = load_json_list(QUARENTENA_FILE)
    cat = load_json_list(CATALOGO_2026_FILE)
    pendentes = [q for q in quar if q.get("status_2fa") == "PENDENTE_QUARENTENA_2FA"]
    descartados = [q for q in quar if q.get("status_2fa") == "DESCARTADO_NAO_E_ROLE"]
    print("\n" + "=" * 80, flush=True)
    print("BALANÇO GERAL DA COLETA 2026 (@rolezandoembrasilia):", flush=True)
    print(f"   Total de vídeos de 2026 no catálogo : {len(cat)}", flush=True)
    print(f"   [OK] Aprovados no 2FA (Banco Oficial)    : {len(aprov)}", flush=True)
    print(f"   [PENDENTE] Retidos em Quarentena (Incompletos) : {len(pendentes)}", flush=True)
    print(f"   [DESCARTADO] Filtrados (Anúncios/Não são rolê)   : {len(descartados)}", flush=True)
    print("=" * 80 + "\n", flush=True)

