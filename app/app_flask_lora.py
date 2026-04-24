"""
FarmSense — app_flask_lora.py
==============================
Version avec poids LoRA fine-tunés chargés directement depuis HuggingFace.
Utilise transformers + peft au lieu d'Ollama — donne les vraies réponses
du modèle fine-tuné FarmSense-Gemma4.

Usage :
    HF_TOKEN=hf_xxx python app_flask_lora.py
"""

import base64
import io
import json
import os
import tempfile

import torch
from flask import Flask, jsonify, render_template, request
from gtts import gTTS
from PIL import Image as PILImage
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

from tools import TOOL_FUNCTIONS


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_MODEL  = "unsloth/gemma-4-E4B-it"
LORA_MODEL  = "ndaosaer/farmsense-gemma4"
HF_TOKEN    = os.getenv("HF_TOKEN", "")

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

URGENCES — ergot du sorgho ou mosaïque du manioc :
- Commence par "URGENT :" en majuscules

Quand des données de diagnostic, météo ou prix sont fournies, utilise-les.
"""

# ---------------------------------------------------------------------------
# Chargement du modèle (au démarrage — une seule fois)
# ---------------------------------------------------------------------------
print("Chargement du modèle FarmSense fine-tuné...")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    token=HF_TOKEN,
    trust_remote_code=True
)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map={"": 0},
    token=HF_TOKEN,
    trust_remote_code=True
)

# Charger les poids LoRA fine-tunés
model = PeftModel.from_pretrained(
    base_model,
    LORA_MODEL,
    token=HF_TOKEN,
)
model.eval()
print(f"✅ Modèle FarmSense chargé — {LORA_MODEL}")


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
# Route : statut
# ---------------------------------------------------------------------------
@app.route("/status")
def status():
    return jsonify({
        "ready":   True,
        "model":   LORA_MODEL,
        "message": "Modèle FarmSense fine-tuné chargé"
    })


# ---------------------------------------------------------------------------
# Détection des besoins et appel des outils
# ---------------------------------------------------------------------------
def run_tools(message: str, location: str, language: str) -> list:
    msg = message.lower()
    results = []

    maladie_mots = [
        "jauni", "tache", "taches", "maladie", "feuille", "feuilles",
        "plante", "champignon", "pourri", "flétr", "moisissure",
        "insecte", "ravageur", "malade", "photo", "image", "analyse",
        "garab", "daan", "set"
    ]
    if any(k in msg for k in maladie_mots):
        crop = None
        for c in ["mil", "sorgho", "arachide", "tomate", "niébé", "niebe",
                  "manioc", "maïs", "mais", "oignon", "riz"]:
            if c in msg:
                crop = c
                break
        result = TOOL_FUNCTIONS["search_disease"](
            symptoms=[message[:300]], crop=crop, language=language
        )
        results.append(f"DIAGNOSTIC:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

    meteo_mots = ["météo", "meteo", "pluie", "température", "arroser",
                  "arrosage", "semaine", "temps", "ndaw", "sanqal"]
    if any(k in msg for k in meteo_mots):
        loc = location.lower()
        result = TOOL_FUNCTIONS["get_weather"](location=loc)
        results.append(f"MÉTÉO:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

    prix_mots = ["prix", "marché", "marche", "vendre", "vente", "fcfa",
                 "combien", "xaalis", "jaay"]
    if any(k in msg for k in prix_mots):
        crop_prix = None
        for c in ["arachide", "mil", "sorgho", "tomate", "niébé",
                  "manioc", "maïs", "oignon", "riz"]:
            if c in msg:
                crop_prix = c
                break
        result = TOOL_FUNCTIONS["get_market_prices"](crop=crop_prix)
        results.append(f"PRIX MARCHÉ:\n{json.dumps(result, ensure_ascii=False, indent=2)}")

    return results


# ---------------------------------------------------------------------------
# Génération de la réponse avec le modèle fine-tuné
# ---------------------------------------------------------------------------
def generate_response(message: str, tool_results: list,
                       image_b64: str = None) -> str:
    """
    Génère une réponse avec le modèle FarmSense fine-tuné.
    """
    # Enrichir le message avec les résultats des outils
    if tool_results:
        context = "\n\n".join(tool_results)
        full_message = (
            f"{message}\n\n"
            f"=== Données disponibles ===\n{context}\n"
            f"=== Fin des données ===\n\n"
            f"Utilise ces données pour répondre."
        )
    else:
        full_message = message

    # Construire le prompt au format Gemma 4
    messages = [
        {"role": "system",    "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
        {"role": "user",      "content": [{"type": "text", "text": full_message}]}
    ]

    # Ajouter l'image si fournie
    if image_b64:
        img_bytes = base64.b64decode(image_b64)
        img = PILImage.open(io.BytesIO(img_bytes))
        messages[1]["content"].insert(0, {"type": "image", "image": img})

    # Tokeniser
    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt"
    ).to("cuda")

    # Générer
    with torch.no_grad():
        outputs = model.generate(
            input_ids=inputs,
            max_new_tokens=300,
            temperature=0.2,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    response = tokenizer.decode(
        outputs[0][inputs.shape[1]:],
        skip_special_tokens=True
    )
    return response.strip()


# ---------------------------------------------------------------------------
# Synthèse vocale
# ---------------------------------------------------------------------------
_WOLOF_MARKERS = {
    "jëfandikoo", "dafa", "tàkk", "jaap", "ndox", "garab",
    "nit", "dëkk", "suba", "bëgg", "wàcc", "jël", "ci", "bi", "yi"
}

def text_to_speech(text: str, language: str = "fr") -> str | None:
    try:
        if language == "wo":
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
        return None


# ---------------------------------------------------------------------------
# Route chat
# ---------------------------------------------------------------------------
@app.route("/chat", methods=["POST"])
def chat():
    data     = request.get_json()
    message  = data.get("message", "")
    language = data.get("language", "fr")
    location = data.get("location", "Kaolack")
    image    = data.get("image")

    if not message and not image:
        return jsonify({"error": "Message vide"})

    lang_label = "Français" if language == "fr" else "Wolof"
    context    = f"[Zone : {location} | Langue : {lang_label}]"
    full_msg   = f"{context}\n{message or 'Analyse cette photo de ma plante.'}"

    # Traiter l'image
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

    # Appeler les outils
    msg_for_tools = message or ""
    if image_b64:
        msg_for_tools += " photo maladie feuille plante"

    tool_results = run_tools(msg_for_tools, location, language)

    # Générer la réponse
    try:
        response = generate_response(full_msg, tool_results, image_b64)
    except Exception as e:
        return jsonify({"error": f"Erreur : {str(e)}"})

    audio = text_to_speech(response, language=language)
    return jsonify({"response": response, "audio": audio})


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"FarmSense LoRA → http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=False)
