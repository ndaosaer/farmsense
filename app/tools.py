"""
FarmSense — tools.py
====================
Les 3 outils que Gemma 4 peut appeler automatiquement via function calling.

  - search_disease  : diagnostique une maladie depuis la base locale (offline)
  - get_weather     : météo 3 jours pour une zone du Sénégal (Open-Meteo, gratuit)
  - get_market_prices : prix des cultures en FCFA/kg

Ce fichier est indépendant de l'interface. Il peut être testé seul.
"""

import json
import requests
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Chargement de la base de maladies (fichier local — fonctionne offline)
# ---------------------------------------------------------------------------
_DB_PATH = Path(__file__).parent.parent / "data" / "diseases.json"


def _load_disease_db() -> list:
    with open(_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["diseases"]


DISEASE_DB = _load_disease_db()


# ---------------------------------------------------------------------------
# OUTIL 1 — Recherche de maladie
# ---------------------------------------------------------------------------
def search_disease(
    symptoms: list = None,
    symptom: str = None,
    crop: str = None,
    language: str = "fr",
    **kwargs          # ← capture TOUT argument inattendu que Gemma 4 invente
) -> dict:
    """
    Cherche la maladie la plus probable d'après les symptômes visuels décrits
    ou observés sur la photo. Fonctionne 100% offline.

    Paramètres
    ----------
    symptoms : list[str], optional
        Liste de symptômes, ex: ["taches jaunes", "poudre grise"]
    symptom : str, optional
        Symptôme unique — Gemma 4 utilise parfois le singulier.
    crop : str, optional
        Culture concernée, ex: "mil", "arachide", "tomate"
    language : str
        "fr" pour français, "wo" pour wolof
    **kwargs
        Capture tous les arguments inattendus que Gemma 4 pourrait inventer
        (ex: "plante", "culture", "description"...).
        On les récupère ici pour ne pas planter, et on essaie de les réutiliser.
    """
    # Récupérer les arguments inattendus de kwargs
    # Gemma 4 envoie parfois "plante" à la place de "crop"
    if crop is None:
        crop = kwargs.get("plante") or kwargs.get("culture") or kwargs.get("plant")

    # Gemma 4 envoie parfois "description" ou "symptomes" (sans accent) à la place de "symptoms"
    if symptoms is None and symptom is None:
        fallback = (
            kwargs.get("symptomes") or
            kwargs.get("description") or
            kwargs.get("observations") or
            kwargs.get("probleme")
        )
        if fallback:
            symptoms = fallback if isinstance(fallback, list) else [fallback]

    # Unifier symptom (singulier) et symptoms (pluriel) en une seule liste
    if symptoms is None and symptom is not None:
        symptoms = symptom if isinstance(symptom, list) else [symptom]

    if not symptoms:
        return {"error": "Aucun symptôme fourni"}

    symptoms_lower = [s.lower() for s in symptoms]
    scored = []

    for disease in DISEASE_DB:

        # Si une culture est précisée, on ne garde que les maladies qui la touchent
        if crop:
            crop_match = any(crop.lower() in c.lower() for c in disease["crops"])
            if not crop_match:
                continue

        # Score de correspondance avec les symptômes de la base
        score = 0
        for db_symptom in disease["visual_symptoms"]:
            for user_symptom in symptoms_lower:
                words = db_symptom.lower().split()
                if any(w in user_symptom or user_symptom in w for w in words if len(w) > 3):
                    score += 1

        if score > 0:
            scored.append((score, disease))

    if not scored:
        return {
            "found": False,
            "message_fr": "Aucune maladie connue ne correspond aux symptômes dans la base. "
                          "Consultez un agent agricole local.",
            "message_wo": "Maladie bi amul ci base bi. Jëfandikoo agent agricole bi."
        }

    # Garder le meilleur score
    scored.sort(key=lambda x: x[0], reverse=True)
    _, best = scored[0]

    lang = "wo" if language == "wo" else "fr"

    return {
        "found": True,
        "disease_name": best.get(f"name_{lang}", best["name_fr"]),
        "cause": best["cause"],
        "severity": best["severity"],
        "urgency_days": best["urgency_days"],
        "treatment": best.get(f"treatment_{lang}", best["treatment_fr"]),
        "prevention": best["prevention"],
        "crops_affected": best["crops"]
    }


# ---------------------------------------------------------------------------
# OUTIL 2 — Météo locale (Open-Meteo, API gratuite, sans clé)
# ---------------------------------------------------------------------------
ZONES_SENEGAL = {
    "dakar":        (14.6937, -17.4441),
    "thiès":        (14.7833, -16.9167),
    "kaolack":      (14.1500, -16.0667),
    "ziguinchor":   (12.5833, -16.2667),
    "saint-louis":  (16.0333, -16.5167),
    "tambacounda":  (13.7667, -13.6667),
    "kolda":        (12.8833, -14.9500),
    "louga":        (15.6167, -16.2333),
    "fatick":       (14.3333, -16.4000),
    "kaffrine":     (14.1000, -15.5500),
}


def get_weather(location: str = "kaolack", **kwargs) -> dict:
    """
    Prévisions météo des 3 prochains jours pour une zone agricole du Sénégal.
    Inclut des alertes agricoles automatiques (risque fongique, chaleur, etc.).

    Paramètres
    ----------
    location : str
        Ville ou zone, ex: "kaolack", "thiès", "ziguinchor"
    """
    loc = location.lower().strip()
    coords = next(
        (v for k, v in ZONES_SENEGAL.items() if k in loc or loc in k),
        ZONES_SENEGAL["kaolack"]   # Kaolack par défaut (centre agricole)
    )
    lat, lon = coords

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
        f"relative_humidity_2m_max,wind_speed_10m_max"
        f"&timezone=Africa%2FDakar&forecast_days=3"
    )

    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        d = r.json()["daily"]

        forecast = []
        for i in range(3):
            rain     = d["precipitation_sum"][i]
            humidity = d["relative_humidity_2m_max"][i]
            temp_max = d["temperature_2m_max"][i]
            wind     = d["wind_speed_10m_max"][i]

            alerts = []
            if rain > 20:
                alerts.append("Fortes pluies — risque de lessivage des engrais et maladies fongiques")
            elif rain > 5:
                alerts.append("Pluie modérée — bon pour les cultures, surveiller les champignons")
            if humidity > 80:
                alerts.append("Humidité élevée — conditions favorables au mildiou et champignons")
            if temp_max > 38:
                alerts.append("Chaleur intense — arrosez tôt le matin")
            if wind > 40:
                alerts.append("Vent fort — risque de verse pour mil et sorgho")

            forecast.append({
                "date":             d["time"][i],
                "temp_max_c":       temp_max,
                "temp_min_c":       d["temperature_2m_min"][i],
                "rain_mm":          rain,
                "humidity_pct":     humidity,
                "wind_kmh":         wind,
                "agricultural_alerts": alerts
            })

        return {
            "location":   location,
            "forecast":   forecast,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

    except requests.exceptions.ConnectionError:
        return {
            "location": location,
            "mode":     "offline",
            "message":  "Météo indisponible (mode hors ligne). Données types pour la saison.",
            "forecast": [{
                "date":       "aujourd'hui",
                "temp_max_c": 36, "temp_min_c": 24,
                "rain_mm":    0,  "humidity_pct": 55, "wind_kmh": 18,
                "agricultural_alerts": ["Données météo non disponibles — consultez la radio locale"]
            }]
        }


# ---------------------------------------------------------------------------
# OUTIL 3 — Prix du marché (base JSON locale, mise à jour manuelle)
# ---------------------------------------------------------------------------
# Prix moyens en FCFA/kg — Sénégal, Avril 2026
# Source : marchés locaux, ANSD, agents terrain
PRIX_MARCHE = {
    "mil":       {"price_fcfa_kg": 175, "trend": "stable",   "best_market": "Thiès, Diourbel"},
    "sorgho":    {"price_fcfa_kg": 155, "trend": "hausse",   "best_market": "Kaolack, Fatick"},
    "arachide":  {"price_fcfa_kg": 350, "trend": "hausse",   "best_market": "Kaolack, Ziguinchor"},
    "maïs":      {"price_fcfa_kg": 160, "trend": "baisse",   "best_market": "Saint-Louis, Louga"},
    "niébé":     {"price_fcfa_kg": 450, "trend": "stable",   "best_market": "Kolda, Kaffrine"},
    "manioc":    {"price_fcfa_kg": 80,  "trend": "stable",   "best_market": "Ziguinchor, Kolda"},
    "tomate":    {"price_fcfa_kg": 300, "trend": "variable", "best_market": "Dakar (Sandaga)"},
    "oignon":    {"price_fcfa_kg": 250, "trend": "hausse",   "best_market": "Saint-Louis, Louga"},
    "riz local": {"price_fcfa_kg": 400, "trend": "stable",   "best_market": "Casamance, Delta du Fleuve"},
}


def get_market_prices(crop: str = None, **kwargs) -> dict:
    """
    Prix actuels du marché pour une culture donnée, ou toutes les cultures.

    Paramètres
    ----------
    crop : str, optional
        Nom de la culture, ex: "arachide", "mil". Si None, retourne tout.
    **kwargs
        Capture les noms alternatifs que Gemma 4 peut utiliser :
        "commodity", "culture", "produit", "item", "plant"
    """
    # Gemma 4 utilise parfois d'autres noms à la place de "crop"
    if crop is None:
        crop = (
            kwargs.get("commodity") or
            kwargs.get("culture")   or
            kwargs.get("produit")   or
            kwargs.get("item")      or
            kwargs.get("plant")
        )

    if crop:
        crop_lower = crop.lower().strip()
        match = next(
            ({"crop": k, **v} for k, v in PRIX_MARCHE.items() if k in crop_lower or crop_lower in k),
            None
        )
        if match:
            return {
                **match,
                "updated":  "Avril 2026",
                "unit":     "FCFA/kg",
                "conseil":  f"Tendance {match['trend']} — meilleur marché : {match['best_market']}"
            }
        return {
            "found": False,
            "message": f"Prix non disponible pour '{crop}'.",
            "available": list(PRIX_MARCHE.keys())
        }

    return {
        "all_prices": PRIX_MARCHE,
        "updated":    "Avril 2026",
        "unit":       "FCFA/kg"
    }


# ---------------------------------------------------------------------------
# Définitions des outils au format Ollama / Gemma 4 function calling
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "name": "search_disease",
        "description": (
            "Recherche une maladie agricole dans la base de données locale du Sahel "
            "à partir de symptômes visuels. À appeler dès qu'une plante semble malade."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symptoms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Liste de symptômes visuels observés, ex: ['taches jaunes', 'poudre grise']"
                },
                "symptom": {
                    "type": "string",
                    "description": "Symptôme unique observé — utiliser si un seul symptôme est identifié"
                },
                "crop": {
                    "type": "string",
                    "description": "Culture concernée, ex: 'mil', 'arachide', 'tomate'"
                },
                "language": {
                    "type": "string",
                    "enum": ["fr", "wo"],
                    "description": "'fr' pour français, 'wo' pour wolof"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_weather",
        "description": (
            "Prévisions météo 3 jours pour une zone agricole du Sénégal, "
            "avec alertes agricoles spécifiques (risque fongique, chaleur, etc.)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Ville ou zone du Sénégal, ex: 'kaolack', 'thiès', 'ziguinchor'"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "get_market_prices",
        "description": (
            "Prix actuels du marché en FCFA/kg pour les cultures agricoles au Sénégal. "
            "À appeler quand l'agriculteur demande le prix ou veut vendre."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "crop": {
                    "type": "string",
                    "description": "Culture concernée. Laisser vide pour toutes les cultures."
                }
            },
            "required": []
        }
    }
]

# Correspondance nom → fonction Python (utilisé dans app.py)
TOOL_FUNCTIONS = {
    "search_disease":    search_disease,
    "get_weather":       get_weather,
    "get_market_prices": get_market_prices,
}
