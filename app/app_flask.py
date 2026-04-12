"""
FarmSense — app_flask.py
========================
Serveur Flask remplaçant Gradio.
Plus stable sur Kaggle, fonctionne avec ngrok pour le lien public.

Routes :
  GET  /          → interface HTML
  GET  /status    → état du modèle Ollama
  POST /chat      → envoie un message à Gemma 4, retourne la réponse + audio
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

from tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_URL  = os.getenv("OLLAMA_URL",  "http://localhost:11434")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4:e4b")

SYSTEM_PROMPT = """Tu es FarmSense, un assistant agricole pour les petits agriculteurs du Sénégal et du Sahel.
Tu parles Français et Wolof. Tu es direct, pratique, et tu parles comme un ami agriculteur — pas comme un médecin.

RÈGLES DE FORMAT — TRÈS IMPORTANTES :
- JAMAIS de markdown : pas de #, pas de **, pas de *, pas de tirets de liste
- Écris en texte simple, comme un SMS ou une conversation orale
- Maximum 8 lignes par réponse
- Structure ta réponse EXACTEMENT ainsi :
    Ligne 1 : Le diagnostic en une phrase (ex: "C'est le Mildiou du mil.")
    Ligne 2 : La cause en une phrase simple (ex: "C'est un champignon qui aime l'humidité.")
    Lignes 3-6 : Les actions numérotées simplement (1. 2. 3.)
    Dernière ligne : "Action immédiate : ..." (une seule chose à faire aujourd'hui)

RÈGLES DE LANGUE :
- Si le contexte indique Wolof, réponds ENTIÈREMENT en Wolof
- Si le contexte indique Français, réponds en Français
- Ne mélange pas les deux langues dans une même réponse

RÈGLES D'OUTILS — utilise TOUJOURS :
- search_disease dès qu'une plante semble malade
- get_weather pour tout conseil lié à la météo ou à l'arrosage
- get_market_prices dès qu'on parle de vente ou de prix

URGENCES — si c'est l'ergot du sorgho ou la mosaïque du manioc :
- Commence par "URGENT :" en majuscules
- Dis que les grains/plants sont dangereux à consommer
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
# Appel Gemma 4 avec boucle function calling
# ---------------------------------------------------------------------------
def call_gemma(messages: list, image_b64: str = None) -> str:
    """
    Envoie les messages à Gemma 4 via Ollama.
    Gère la boucle function calling jusqu'à 3 appels d'outils.
    """
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


  messages = [
    {"role": "system", "content": SYSTEM_PROMPT + "\n\nIMPORTANT : Tu DOIS utiliser les outils disponibles. Ne jamais écrire le nom d'un outil comme réponse texte. Appelle-les directement."}
] + messages
    # Boucle function calling
    for _ in range(3):
        payload = {
            "model":    GEMMA_MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "tools":    TOOL_DEFINITIONS,
            "stream":   False,
            "options": {"temperature": 0.1, "num_ctx": 4096},
            "format": ""
        }

        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        msg = r.json()["message"]

        # Pas d'appel d'outil → réponse finale
        if not msg.get("tool_calls"):
            return msg["content"]

        # Exécuter les outils demandés
        messages.append({
            "role":       "assistant",
            "content":    msg.get("content", ""),
            "tool_calls": msg["tool_calls"]
        })

        for call in msg["tool_calls"]:
            fn_name = call["function"]["name"]
            fn_args = call["function"].get("arguments", {})
            if isinstance(fn_args, str):
                fn_args = json.loads(fn_args)

            if fn_name in TOOL_FUNCTIONS:
                result = TOOL_FUNCTIONS[fn_name](**fn_args)
            else:
                result = {"error": f"Outil inconnu : {fn_name}"}

            messages.append({
                "role":    "tool",
                "name":    fn_name,
                "content": json.dumps(result, ensure_ascii=False)
            })

    return "Je n'ai pas pu finaliser le diagnostic. Veuillez réessayer."


# ---------------------------------------------------------------------------
# Synthèse vocale
# ---------------------------------------------------------------------------
_WOLOF_MARKERS = {
    "jëfandikoo", "dafa", "tàkk", "jaap", "ndox", "garab",
    "nit", "dëkk", "suba", "bëgg", "xamne", "wàcc", "jël",
    "topp", "neem", "yëgël", "ci", "bi", "yi", "bu"
}

def text_to_speech(text: str, language: str = "fr") -> str | None:
    """
    Génère un MP3 et retourne son contenu encodé en base64.
    Wolof → moteur hausa (ha), meilleure approximation disponible dans gTTS.
    """
    try:
        if language == "wo":
            words = set(text.lower().split())
            gtts_lang = "ha" if len(words & _WOLOF_MARKERS) >= 2 else "fr"
        else:
            gtts_lang = "fr"

        tts = gTTS(text=text[:500], lang=gtts_lang, slow=False)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.save(tmp.name)

        # Lire le fichier et l'encoder en base64 pour l'envoyer au client
        with open(tmp.name, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.unlink(tmp.name)
        return audio_b64

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Route principale : chat
# ---------------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    """
    Reçoit : { message, language, location, image (base64), history }
    Retourne : { response, audio (base64) }
    """
    data     = request.get_json()
    message  = data.get("message", "")
    language = data.get("language", "fr")
    location = data.get("location", "Kaolack")
    image    = data.get("image")      # base64 JPEG ou None
    history  = data.get("history", [])

    if not message and not image:
        return jsonify({"error": "Message vide"})

    # Enrichir avec le contexte de l'agriculteur
    lang_label = "Français" if language == "fr" else "Wolof"
    context    = f"[Zone : {location} | Langue : {lang_label}]"
    full_msg   = f"{context}\n{message or 'Analyse cette photo de ma plante.'}"

    # Construire les messages au format Ollama
    messages = []
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": full_msg})

    # Redimensionner l'image si fournie (réduit la mémoire GPU)
    image_b64 = None
    if image:
        try:
            img_bytes = base64.b64decode(image)
            img       = PILImage.open(io.BytesIO(img_bytes))
            # Limiter à 800px max pour économiser la mémoire
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            return jsonify({"error": f"Image invalide : {str(e)}"})

    # Appel Gemma 4
    try:
        response = call_gemma(messages, image_b64)
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Ollama non disponible. Relancez le serveur."})
    except Exception as e:
        return jsonify({"error": f"Erreur : {str(e)}"})

    # Synthèse vocale
    audio = text_to_speech(response, language=language)

    return jsonify({"response": response, "audio": audio})


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"FarmSense démarré sur http://0.0.0.0:5000")
    print(f"Modèle : {GEMMA_MODEL}")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
