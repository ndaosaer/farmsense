"""
FarmSense — app_flask.py
========================
Serveur Flask stable pour Kaggle + ngrok.

Stratégie d'appel des outils :
  On n'utilise PAS le function calling natif de Gemma 4 (instable sur e4b).
  À la place, on détecte les besoins côté Python, on appelle les outils
  directement, on injecte les résultats dans le contexte, puis Gemma génère
  une réponse finale enrichie. C'est plus fiable et plus rapide.

Routes :
  GET  /        → interface HTML
  GET  /status  → état du modèle Ollama
  POST /chat    → message + photo → réponse texte + audio base64
"""

import base64
import io
import json
import os
import tempfile

import requests
from flask import Flask, jsonify, render_template, request
from gtts import gTTS
from PIL import Image as PILImage

from tools import TOOL_FUNCTIONS


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_URL  = os.getenv("OLLAMA_URL",  "http://localhost:11434")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4:e4b")

SYSTEM_PROMPT = """Tu es FarmSense, un assistant agricole pour les petits agriculteurs du Sénégal et du Sahel.
Tu parles Français et Wolof. Tu es direct, pratique, et tu parles comme un ami agriculteur.

RÈGLES DE FORMAT — OBLIGATOIRES :
- JAMAIS de markdown : pas de #, pas de **, pas de *, pas de tirets, pas de tableaux
- Texte simple uniquement, comme un SMS ou une conversation orale
- Maximum 8 lignes par réponse
- Structure ta réponse EXACTEMENT ainsi :
    Ligne 1 : Le diagnostic en une phrase
    Ligne 2 : La cause en une phrase simple
    Lignes 3-6 : Les actions numérotées (1. 2. 3.)
    Dernière ligne : "Action immédiate : ..." (une seule chose à faire aujourd'hui)

RÈGLES DE LANGUE :
- Si le contexte indique Wolof → réponds ENTIÈREMENT en Wolof
- Si le contexte indique Français → réponds en Français
- Ne mélange jamais les deux langues

URGENCES — ergot du sorgho ou mosaïque du manioc :
- Commence par "URGENT :" en majuscules
- Précise que les grains/plants sont dangereux à consommer

Quand des données de diagnostic, météo ou prix sont fournies dans le contexte,
utilise-les pour donner des conseils précis et concrets.
"""


# ---------------------------------------------------------------------------
# Application Flask
# ---------------------------------------------------------------------------
app = Flask(__name__)


# ---------------------------------------------------------------------------
# Route : page d'accueil
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Route : statut du modèle
# ---------------------------------------------------------------------------
@app.route("/status")
def status():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in r.json().get("models", [])]
        model_ok = any("gemma4" in m for m in models)
        return jsonify({
            "ready":   model_ok,
            "model":   GEMMA_MODEL,
            "message": "Modèle chargé" if model_ok else "Modèle non trouvé"
        })
    except Exception as e:
        return jsonify({"ready": False, "model": GEMMA_MODEL, "message": str(e)})


# ---------------------------------------------------------------------------
# Détection automatique des besoins et appel des outils côté Python
# ---------------------------------------------------------------------------
def run_tools(message: str, location: str, language: str) -> list:
    """
    Analyse le message et appelle les outils Python nécessaires.
    Retourne une liste de strings avec les résultats à injecter dans le contexte.

    On ne passe plus par le function calling de Gemma 4 (instable) —
    on détecte les besoins ici et on appelle directement les fonctions Python.
    """
    msg = message.lower()
    results = []

    # ── Outil 1 : Diagnostic maladie ──────────────────────────────────
    # Déclenché si symptômes visibles ou photo envoyée
    maladie_mots = [
        "jauni", "tache", "taches", "maladie", "feuille", "feuilles",
        "plante", "champignon", "pourri", "flétr", "déform", "moisissure",
        "insecte", "ravageur", "symptôme", "problème", "malade", "mort",
        "sèche", "brûl", "photo", "image", "analyse", "regarde",
        "garab", "daan", "set", "xam"
    ]
    if any(k in msg for k in maladie_mots):
        # Détecter la culture mentionnée
        crop = None
        for c in ["mil", "sorgho", "arachide", "tomate", "niébé", "niebe",
                  "manioc", "maïs", "mais", "oignon", "riz", "haricot"]:
            if c in msg:
                crop = c
                break

        # Les symptômes = le message lui-même
        symptoms = [message[:300]]

        result = TOOL_FUNCTIONS["search_disease"](
            symptoms=symptoms,
            crop=crop,
            language=language
        )
        results.append(f"DIAGNOSTIC:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

    # ── Outil 2 : Météo ───────────────────────────────────────────────
    # Déclenché si question sur météo, arrosage, pluie, semaine
    meteo_mots = [
        "météo", "meteo", "pluie", "température", "chaleur", "vent",
        "arroser", "arrosage", "semaine", "temps", "saison", "humidité",
        "ndaw", "sanqal", "ndox bi", "loxo"
    ]
    if any(k in msg for k in meteo_mots):
        # Détecter la zone dans le message
        loc = location.lower()
        for zone in ["dakar", "thiès", "thies", "kaolack", "ziguinchor",
                     "saint-louis", "tambacounda", "kolda", "louga",
                     "fatick", "kaffrine"]:
            if zone in msg:
                loc = zone
                break

        result = TOOL_FUNCTIONS["get_weather"](location=loc)
        results.append(f"MÉTÉO:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

    # ── Outil 3 : Prix du marché ──────────────────────────────────────
    # Déclenché si question sur prix, vente, marché
    prix_mots = [
        "prix", "marché", "marche", "vendre", "vente", "fcfa", "cfa",
        "argent", "coût", "cout", "valeur", "combien", "acheter",
        "achat", "xaalis", "jaay", "jënd"
    ]
    if any(k in msg for k in prix_mots):
        # Détecter la culture pour le prix
        crop_prix = None
        for c in ["arachide", "mil", "sorgho", "tomate", "niébé", "niebe",
                  "manioc", "maïs", "mais", "oignon", "riz local", "riz"]:
            if c in msg:
                crop_prix = c
                break

        result = TOOL_FUNCTIONS["get_market_prices"](crop=crop_prix)
        results.append(f"PRIX MARCHÉ:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

    return results


# ---------------------------------------------------------------------------
# Appel Gemma 4 — sans function calling, contexte enrichi
# ---------------------------------------------------------------------------
def call_gemma(messages: list, image_b64: str = None,
               tool_results: list = None) -> str:
    """
    Envoie le message à Gemma 4 avec les résultats des outils
    déjà injectés dans le contexte.

    Paramètres
    ----------
    messages     : historique de conversation au format Ollama
    image_b64    : image encodée en base64 (optionnel)
    tool_results : liste de strings avec les résultats des outils
    """
    # Enrichir le dernier message avec les résultats des outils
    if tool_results:
        last = messages[-1]
        last_content = (
            last["content"]
            if isinstance(last["content"], str)
            else str(last["content"])
        )
        context_block = "\n\n".join(tool_results)
        enriched_content = (
            f"{last_content}\n\n"
            f"=== Données disponibles pour ta réponse ===\n"
            f"{context_block}\n"
            f"=== Fin des données ===\n\n"
            f"Utilise ces données pour donner une réponse précise et courte."
        )
        messages = messages[:-1] + [{"role": "user", "content": enriched_content}]

    # Ajouter l'image au dernier message si fournie
    if image_b64:
        last = messages[-1]
        if isinstance(last["content"], str):
            messages[-1] = {
                "role": "user",
                "content": [
                    {"type": "image", "data": image_b64},
                    {"type": "text",  "text": last["content"]}
                ]
            }

    # Appel Gemma 4 — sans outils pour éviter les blocages
    payload = {
        "model":    GEMMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream":   False,
        "options":  {"temperature": 0.2, "num_ctx": 4096}
    }

    r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
    r.raise_for_status()

    content = r.json().get("message", {}).get("content", "")
    return (
        content.strip()
        if content.strip()
        else "Je n'ai pas pu générer une réponse. Veuillez réessayer."
    )


# ---------------------------------------------------------------------------
# Synthèse vocale — Français et Wolof
# ---------------------------------------------------------------------------
_WOLOF_MARKERS = {
    "jëfandikoo", "dafa", "tàkk", "jaap", "ndox", "garab",
    "nit", "dëkk", "suba", "bëgg", "xamne", "wàcc", "jël",
    "topp", "neem", "yëgël", "ci", "bi", "yi", "bu", "xam"
}


def text_to_speech(text: str, language: str = "fr") -> str | None:
    """
    Génère un fichier audio MP3 et le retourne encodé en base64.

    Le Wolof n'est pas supporté nativement par gTTS.
    On utilise le moteur hausa ("ha") qui est phonétiquement
    le plus proche parmi les langues disponibles.
    """
    try:
        if language == "wo":
            # Vérifier si le texte contient vraiment du wolof
            words = set(text.lower().split())
            gtts_lang = "ha" if len(words & _WOLOF_MARKERS) >= 2 else "fr"
        else:
            gtts_lang = "fr"

        tts = gTTS(text=text[:500], lang=gtts_lang, slow=False)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.save(tmp.name)

        with open(tmp.name, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.unlink(tmp.name)
        return audio_b64

    except Exception:
        # Fallback silencieux — pas d'audio plutôt qu'une erreur
        return None


# ---------------------------------------------------------------------------
# Route principale : chat
# ---------------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """
    Reçoit : { message, language, location, image (base64), history }
    Retourne : { response (str), audio (base64 ou null) }
    """
    data     = request.get_json()
    message  = data.get("message", "")
    language = data.get("language", "fr")
    location = data.get("location", "Kaolack")
    image    = data.get("image")
    history  = data.get("history", [])

    if not message and not image:
        return jsonify({"error": "Message vide"})

    # Enrichir le message avec le contexte de l'agriculteur
    lang_label = "Français" if language == "fr" else "Wolof"
    context    = f"[Zone : {location} | Langue : {lang_label}]"
    full_msg   = f"{context}\n{message or 'Analyse cette photo de ma plante.'}"

    # Construire l'historique au format Ollama
    messages = []
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": full_msg})

    # Traiter l'image si fournie
    image_b64 = None
    if image:
        try:
            img_bytes = base64.b64decode(image)
            img       = PILImage.open(io.BytesIO(img_bytes))
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            return jsonify({"error": f"Image invalide : {str(e)}"})

    # Appeler les outils nécessaires côté Python
    msg_for_tools = message or ""
    if image_b64:
        # Photo envoyée → forcer le diagnostic maladie
        msg_for_tools += " photo maladie feuille plante analyse"

    tool_results = run_tools(
        message=msg_for_tools,
        location=location,
        language=language
    )

    # Appeler Gemma 4 avec le contexte enrichi
    try:
        response = call_gemma(messages, image_b64, tool_results)
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Ollama non disponible. Relancez le serveur Ollama."})
    except Exception as e:
        return jsonify({"error": f"Erreur : {str(e)}"})

    # Générer la réponse audio
    audio = text_to_speech(response, language=language)

    return jsonify({"response": response, "audio": audio})


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"FarmSense démarré → http://0.0.0.0:5000")
    print(f"Modèle : {GEMMA_MODEL}")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
