"""Mapeamento das categorias da Overture (taxonomia de 2026) para as categorias e tipos de rolê do esquema."""

# Categoria nossa → tipo de rolê
TIPO = {
    "restaurante": "comer_beber", "bar": "comer_beber", "cafe": "comer_beber",
    "lanchonete": "comer_beber", "sorveteria": "comer_beber",
    "parque": "ar_livre_gratuito", "mirante": "ar_livre_gratuito", "feira": "ar_livre_gratuito",
    "museu": "ar_livre_gratuito", "outro": "ar_livre_gratuito",
    "centro_cultural": "local_evento", "teatro": "local_evento", "casa_de_show": "local_evento",
}

# Estrato do sorteio dentro do tipo (ADR 0004, divisão por tipo)
def estrato(categoria: str) -> str:
    if categoria in ("restaurante", "bar"):
        return categoria
    if categoria in ("cafe", "lanchonete", "sorveteria"):
        return "cafe_lanchonete_sorveteria"
    return TIPO[categoria]

# taxonomy.primary tem precedência; basic_category é o fallback.
_POR_PRIMARIA = {
    "ice_cream_shop": "sorveteria", "gelato_shop": "sorveteria", "frozen_yogurt_shop": "sorveteria",
    "dessert_shop": "sorveteria",
    "bakery": "lanchonete", "sandwich_shop": "lanchonete", "hot_dog_restaurant": "lanchonete",
    "pancake_house": "lanchonete", "cafeteria": "cafe", "tea_room": "cafe",
    "gastropub": "bar", "tapas_bar": "bar", "pub": "bar", "beer_bar": "bar", "wine_bar": "bar",
    "cocktail_bar": "bar", "sports_bar": "bar",
}
_POR_BASICA = {
    "restaurant": "restaurante",
    "fast_food_restaurant": "lanchonete", "casual_eatery": "lanchonete", "food_truck_stand": "lanchonete",
    "smoothie_juice_bar": "lanchonete", "food_court": "lanchonete",
    "cafe": "cafe", "coffee_shop": "cafe",
    "bar": "bar", "brewery": "bar", "lounge": "bar", "winery": "bar",
    "park": "parque", "garden": "parque", "nature_reserve": "parque",
    "zoo": "outro",
    "farmers_market": "feira", "market": "feira",
    "museum": "museu", "art_gallery": "museu",
    "cultural_center": "centro_cultural",
    "theatre_venue": "teatro", "performing_arts_venue": "teatro",
    "music_venue": "casa_de_show", "dance_club": "casa_de_show", "nightlife_venue": "casa_de_show",
    "comedy_club": "casa_de_show",
}
# Lojas e serviços que caem sob alimentação mas não são rolê
_EXCLUIR_PRIMARIA = {
    "grocery_store", "liquor_store", "butcher_shop", "chocolatier", "candy_store", "food_delivery_service",
    "pizza_delivery_service", "health_food_store", "vitamin_and_supplement_store", "tobacco_shop",
    "produce_store", "organic_grocery_store", "fishmonger", "specialty_foods_store", "cheese_shop",
    "beer_wine_spirits_store", "delicatessen",
}


def mapear(basica: str | None, primaria: str | None, hierarquia: list | None) -> str | None:
    """Categoria do esquema, ou None se o lugar não é um tipo de rolê do MVP."""
    if primaria in _EXCLUIR_PRIMARIA:
        return None
    if primaria in _POR_PRIMARIA:
        return _POR_PRIMARIA[primaria]
    if basica in _POR_BASICA:
        return _POR_BASICA[basica]
    if primaria and primaria.endswith("_restaurant") or primaria in ("steakhouse", "diner"):
        return "restaurante"
    return None
