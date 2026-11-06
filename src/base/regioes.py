"""As 35 RAs do DF, as seis regiões do ADR 0004 e a localização de pontos pelos limites oficiais.

Limites: camada "Regiões Administrativas" do catálogo do IPE-DF (GeoNode), baixada por WFS.
"""
import json

import requests
from shapely import STRtree
from shapely.geometry import Point, shape
from shapely.ops import transform

from .config import RAW

WFS = ("https://catalogo.ipe.df.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature"
       "&typeNames=geonode:regioes_administrativas&outputFormat=application/json&srsName=EPSG:4326")
ARQUIVO = RAW / "ras" / "ras.geojson"

REGIOES = {
    "centro": "Centro",
    "oeste_proximo": "Oeste próximo",
    "oeste": "Oeste",
    "sul": "Sul",
    "norte": "Norte",
    "leste": "Leste",
}

# Código CIRA da RA → (nome, região). Os nomes da camada vêm com a acentuação corrompida, por isso o código manda.
RAS = {
    1: ("Plano Piloto", "centro"), 11: ("Cruzeiro", "centro"), 22: ("Sudoeste/Octogonal", "centro"),
    16: ("Lago Sul", "centro"), 18: ("Lago Norte", "centro"), 23: ("Varjão", "centro"),
    24: ("Park Way", "centro"), 19: ("Candangolândia", "centro"), 29: ("SIA", "centro"),
    3: ("Taguatinga", "oeste_proximo"), 20: ("Águas Claras", "oeste_proximo"), 30: ("Vicente Pires", "oeste_proximo"),
    33: ("Arniqueira", "oeste_proximo"), 10: ("Guará", "oeste_proximo"), 25: ("SCIA/Estrutural", "oeste_proximo"),
    8: ("Núcleo Bandeirante", "oeste_proximo"), 17: ("Riacho Fundo", "oeste_proximo"),
    21: ("Riacho Fundo II", "oeste_proximo"),
    9: ("Ceilândia", "oeste"), 32: ("Sol Nascente/Pôr do Sol", "oeste"), 12: ("Samambaia", "oeste"),
    4: ("Brazlândia", "oeste"),
    2: ("Gama", "sul"), 13: ("Santa Maria", "sul"), 15: ("Recanto das Emas", "sul"), 35: ("Água Quente", "sul"),
    5: ("Sobradinho", "norte"), 26: ("Sobradinho II", "norte"), 6: ("Planaltina", "norte"),
    34: ("Arapoanga", "norte"), 31: ("Fercal", "norte"),
    7: ("Paranoá", "leste"), 28: ("Itapoã", "leste"), 14: ("São Sebastião", "leste"),
    27: ("Jardim Botânico", "leste"),
}


def baixar():
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(WFS, timeout=120)
    r.raise_for_status()
    ARQUIVO.write_bytes(r.content)


def poligonos() -> list[tuple[int, object]]:
    """Lista de (código CIRA, geometria em lon/lat)."""
    if not ARQUIVO.exists():
        baixar()
    feats = json.loads(ARQUIVO.read_text(encoding="utf-8", errors="replace"))["features"]
    geoms = [(int(f["properties"]["ra_cira"]), shape(f["geometry"])) for f in feats]
    # O WFS 2.0 em EPSG:4326 pode vir em lat/lon; o DF tem lon perto de -48 e lat perto de -16.
    if geoms and geoms[0][1].centroid.x > -30:
        geoms = [(c, transform(lambda x, y: (y, x), g)) for c, g in geoms]
    faltam = set(RAS) - {c for c, _ in geoms}
    assert not faltam, f"RAs sem polígono: {faltam}"
    return geoms


class Localizador:
    """Diz em que RA cai um ponto; None fora do DF."""

    def __init__(self):
        self._itens = poligonos()
        self._arvore = STRtree([g for _, g in self._itens])

    def ra(self, lon: float, lat: float):
        p = Point(lon, lat)
        for i in self._arvore.query(p, predicate="intersects"):
            cira = self._itens[int(i)][0]
            nome, regiao = RAS[cira]
            return nome, regiao
        return None

    def vizinhas(self) -> dict[str, list[str]]:
        """RAs que fazem divisa, calculadas pelos polígonos (com folga de cerca de 50 m)."""
        out = {}
        for cira, g in self._itens:
            perto = self._arvore.query(g.buffer(0.0005), predicate="intersects")
            nomes = sorted(RAS[self._itens[int(i)][0]][0] for i in perto if self._itens[int(i)][0] != cira)
            out[RAS[cira][0]] = nomes
        return out
