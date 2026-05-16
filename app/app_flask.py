"""
FarmSense — app_flask.py v2
============================
Architecture hybride :
  - CNN EfficientNet-B0 (99.4% précision) → diagnostic images
  - Gemma 4 fine-tuné → questions textuelles (météo, prix, Wolof)
  - Base phytosanitaire offline → enrichissement des réponses

Routes :
  GET  /        → interface HTML
  GET  /status  → état du modèle
  POST /chat    → message + photo → réponse texte + audio
"""

import base64
import io
import json
import os
import tempfile

import requests
import torch
import torch.nn as nn
from flask import Flask, jsonify, render_template, request
from gtts import gTTS
from PIL import Image as PILImage
from torchvision import models, transforms

from tools import TOOL_FUNCTIONS

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INFER_URL   = os.getenv("INFER_URL",   "http://localhost:8000/infer")
CNN_PATH    = os.getenv("CNN_PATH",    "/tmp/farmsense_cnn.pth")

# Réponses CNN par classe
RESPONSES_CNN = {
    'Tomato___Bacterial_spot':    "Flétrissement bactérien de la tomate : diagnostic confirmé.\nCause : Bactérie Ralstonia solanacearum dans les sols humides argileux.\n1. Arrache et brûle immédiatement les plants malades.\n2. Désinfecte tes outils avec de l'eau de javel à 10%.\n3. Ne replante pas de tomates pendant 3 à 4 ans.\n4. Améliore le drainage de ton sol.\nAction immédiate : Arrache les plants malades aujourd'hui.",
    'Tomato___Early_blight':      "Alternariose de la tomate : diagnostic confirmé.\nCause : Champignon Alternaria solani — alternance pluie et sécheresse.\n1. Retire les feuilles touchées et brûle-les.\n2. Traite au Mancozèbe 2g/L dès aujourd'hui.\n3. Paille le sol autour des plants.\n4. Arrose uniquement à la base.\nAction immédiate : Retire les feuilles malades et traite aujourd'hui.",
    'Tomato___Late_blight':       "Mildiou de la tomate : diagnostic confirmé.\nCause : Champignon Phytophthora infestans — temps humide.\n1. Traite avec Mancozèbe 2g/L immédiatement.\n2. Retire les feuilles et fruits touchés.\n3. Évite l'arrosage le soir.\n4. Améliore la circulation d'air.\nAction immédiate : Traitement fongicide aujourd'hui.",
    'Tomato___Leaf_Mold':         "Moisissure foliaire de la tomate : diagnostic confirmé.\nCause : Champignon Passalora fulva — forte humidité.\n1. Améliore la ventilation — espace les plants.\n2. Traite avec Chlorothalonil 2,5g/L.\n3. Évite l'arrosage par aspersion.\n4. Retire les feuilles touchées.\nAction immédiate : Améliore la ventilation et traite aujourd'hui.",
    'Tomato___Septoria_leaf_spot': "Septoriose de la tomate : diagnostic confirmé.\nCause : Champignon Septoria lycopersici — saison humide.\n1. Retire toutes les feuilles touchées immédiatement.\n2. Traite au Mancozèbe 2g/L toutes les semaines.\n3. Paille le sol pour éviter les éclaboussures.\n4. Évite de mouiller les feuilles.\nAction immédiate : Retire les feuilles malades et traite aujourd'hui.",
    'Tomato___Spider_mites Two-spotted_spider_mite': "Acariens à deux points sur tomate : diagnostic confirmé.\nCause : Tétranyques — temps chaud et sec.\n1. Traite avec Abamectine 0,5mL/L ou soufre mouillable 3g/L.\n2. Arrose le matin — l'humidité réduit les acariens.\n3. Retire les feuilles très infestées.\nAction immédiate : Traitement acaricide aujourd'hui.",
    'Tomato___Target_Spot':       "Tache cible de la tomate : diagnostic confirmé.\nCause : Champignon Corynespora cassiicola — humidité élevée.\n1. Traite au Mancozèbe 2g/L dès aujourd'hui.\n2. Retire les feuilles et fruits touchés.\n3. Améliore la circulation d'air.\nAction immédiate : Traitement fongicide et suppression des parties malades.",
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': "TYLCV : diagnostic confirmé.\nCause : Virus transmis par mouches blanches Bemisia tabaci.\n1. Traite avec Imidaclopride 0,5mL/L contre les mouches blanches.\n2. Arrache et brûle les plants très atteints.\n3. Installe des filets anti-insectes.\nAction immédiate : Traitement insecticide aujourd'hui.",
    'Tomato___Tomato_mosaic_virus': "Mosaïque de la tomate : diagnostic confirmé.\nCause : Virus TMV transmis par contact et outils.\n1. Arrache et brûle les plants malades.\n2. Désinfecte tes outils avec de l'eau de javel.\n3. Utilise des semences certifiées.\nAction immédiate : Arrache les plants malades et désinfecte tes outils.",
    'Tomato___healthy':           "Tes tomates sont saines — aucune maladie visible.\n1. Arrose à la base, jamais sur les feuilles.\n2. Surveille les taches chaque semaine.\n3. Désherbe régulièrement.\nAction immédiate : Continue la surveillance hebdomadaire.",
    'Corn_(maize)___Common_rust_': "Rouille commune du maïs : diagnostic confirmé.\nCause : Champignon Puccinia sorghi — spores par le vent.\n1. Traite avec Propiconazole 0,5mL/L.\n2. Commence préventif 45 jours après semis.\n3. Utilise des variétés résistantes.\nAction immédiate : Traitement fongicide aujourd'hui.",
    'Corn_(maize)___Northern_Leaf_Blight': "Helminthosporiose du maïs : diagnostic confirmé.\nCause : Champignon Exserohilum turcicum — temps humide.\n1. Traite au Mancozèbe 2g/L.\n2. Retire les feuilles très atteintes.\n3. Évite l'excès d'azote.\nAction immédiate : Traitement fongicide et retrait des feuilles malades.",
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot': "Cercosporiose du maïs : diagnostic confirmé.\nCause : Champignon Cercospora zeae-maydis — forte humidité.\n1. Traite au Chlorothalonil 2,5g/L.\n2. Pratique la rotation des cultures.\n3. Retire les résidus de récolte.\nAction immédiate : Traitement fongicide aujourd'hui.",
    'Corn_(maize)___healthy':     "Ton maïs est sain — aucune maladie visible.\n1. Surveille les taches chaque semaine.\n2. Contrôle les foreurs de tiges.\n3. Maintiens une fertilisation équilibrée.\nAction immédiate : Continue la surveillance hebdomadaire.",
    'early_leaf_spot_1':          "Cercosporiose précoce de l'arachide : diagnostic confirmé.\nCause : Champignon Cercospora arachidicola — Bassin arachidier.\n1. Traite avec Chlorothalonil 2,5g/L.\n2. Répète toutes les 2 semaines.\n3. Ramasse et brûle les feuilles tombées.\nAction immédiate : Traitement Chlorothalonil aujourd'hui.",
    'late_leaf_spot_1':           "Cercosporiose tardive de l'arachide : diagnostic confirmé.\nCause : Champignon Cercosporidium personatum — stade avancé.\n1. Traite au Chlorothalonil 2,5g/L immédiatement.\n2. Continue toutes les 2 semaines.\n3. Brûle les feuilles tombées.\nAction immédiate : Traite au Chlorothalonil aujourd'hui.",
    'rust_1':                     "Rouille de l'arachide : diagnostic confirmé.\nCause : Champignon Puccinia arachidis — spores par le vent.\n1. Traite avec Propiconazole 0,5mL/L.\n2. Répète toutes les 3 semaines.\n3. Arrose uniquement au pied.\nAction immédiate : Traitement fongicide aujourd'hui.",
    'early_rust_1':               "Rouille précoce de l'arachide : détectée tôt.\nCause : Champignon Puccinia arachidis — stade précoce traitable.\n1. Traite avec Propiconazole 0,5mL/L immédiatement.\n2. Répète toutes les 3 semaines.\n3. Arrose uniquement à la base.\nAction immédiate : Traitement Propiconazole aujourd'hui.",
    'nutrition_deficiency_1':     "Carence nutritionnelle sur arachide : diagnostic confirmé.\nCause : Sol pauvre en azote — fréquent sur sols sableux du Sahel.\n1. Apporte de l'urée 50kg/hectare.\n2. Si nervures vertes : carence fer — sulfate de fer 2g/L.\n3. Améliore avec compost 3 tonnes/hectare.\nAction immédiate : Apporte engrais azoté ou compost aujourd'hui.",
    'healthy_leaf_1':             "Tes arachides sont saines — aucune maladie visible.\n1. Surveille les taches brunes chaque semaine.\n2. Commence traitements préventifs 45 jours après semis.\n3. Assure rotation avec mil ou sorgho.\nAction immédiate : Continue la surveillance hebdomadaire.",
}

# ---------------------------------------------------------------------------
# Chargement du CNN
# ---------------------------------------------------------------------------
CLASSES = list(RESPONSES_CNN.keys())
IDX_TO_CLASS = {i: c for i, c in enumerate(CLASSES)}

model_cnn = None
cnn_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

def load_cnn():
    global model_cnn, CLASSES, IDX_TO_CLASS
    try:
        checkpoint = torch.load(CNN_PATH, map_location='cuda' if torch.cuda.is_available() else 'cpu')
        CLASSES      = checkpoint['classes']
        IDX_TO_CLASS = checkpoint['idx_to_class']

        cnn = models.efficientnet_b0(weights=None)
        cnn.classifier[1] = nn.Linear(cnn.classifier[1].in_features, len(CLASSES))
        cnn.load_state_dict(checkpoint['model_state_dict'])
        cnn.eval()
        if torch.cuda.is_available():
            cnn = cnn.cuda()
        model_cnn = cnn
        print(f"CNN chargé — {len(CLASSES)} classes")
    except Exception as e:
        print(f"CNN non disponible : {e}")
        model_cnn = None

load_cnn()

# ---------------------------------------------------------------------------
# Application Flask
# ---------------------------------------------------------------------------
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/status")
def status():
    cnn_ok = model_cnn is not None
    return jsonify({
        "ready":   True,
        "model":   "FarmSense CNN + Gemma4 v2",
        "message": f"CNN {'✅' if cnn_ok else '❌'} | LLM via serveur inférence"
    })


# ---------------------------------------------------------------------------
# Diagnostic CNN
# ---------------------------------------------------------------------------
def diagnose_image(image_b64: str, language: str = "fr") -> str:
    """
    Analyse une image avec le CNN EfficientNet.
    Retourne la réponse FarmSense correspondante.
    """
    if model_cnn is None:
        return None

    try:
        img_bytes = base64.b64decode(image_b64)
        img = PILImage.open(io.BytesIO(img_bytes)).convert('RGB')
        tensor = cnn_transform(img).unsqueeze(0)
        if torch.cuda.is_available():
            tensor = tensor.cuda()

        with torch.no_grad():
            outputs = model_cnn(tensor)
            probs   = torch.softmax(outputs, dim=1)
            conf, pred = probs.max(1)

        confidence = conf.item()
        classe     = IDX_TO_CLASS[pred.item()]

        # Confiance trop faible → image non agricole
        if confidence < 0.5:
            if language == "wo":
                return "Foto bi du am garab bu ndéwénél ci cultures yi.\nYónni foto bu dëgël ci feuilles wala parties yu daan ci sa culture."
            return "Je ne reconnais pas de culture agricole sur cette photo.\nEnvoie une photo plus nette en gros plan sur les feuilles ou la partie malade."

        response = RESPONSES_CNN.get(classe, "")
        if not response:
            return None

        # Ajouter la confiance
        conf_text = f"\nConfiance du diagnostic : {confidence:.0%}"
        return response + conf_text

    except Exception as e:
        print(f"Erreur CNN : {e}")
        return None


# ---------------------------------------------------------------------------
# Outils textuels (météo, prix, maladies texte)
# ---------------------------------------------------------------------------
def run_tools(message: str, location: str, language: str) -> list:
    msg = message.lower()
    results = []

    maladie_mots = [
        "jauni", "tache", "maladie", "feuille", "champignon",
        "pourri", "moisissure", "insecte", "malade",
        "garab", "daan", "set"
    ]
    if any(k in msg for k in maladie_mots):
        crop = next((c for c in ["mil","sorgho","arachide","tomate","niébé",
                    "manioc","maïs","oignon","riz"] if c in msg), None)
        result = TOOL_FUNCTIONS["search_disease"](
            symptoms=[message[:300]], crop=crop, language=language)
        results.append(f"DIAGNOSTIC:\n{json.dumps(result, ensure_ascii=False)}")

    prix_mots = ["prix", "marché", "vendre", "fcfa", "combien", "xaalis"]
    if any(k in msg for k in prix_mots):
        crop_p = next((c for c in ["arachide","mil","sorgho","tomate","niébé",
                      "manioc","maïs","oignon","riz"] if c in msg), None)
        result = TOOL_FUNCTIONS["get_market_prices"](crop=crop_p)
        results.append(f"PRIX MARCHÉ:\n{json.dumps(result, ensure_ascii=False)}")

    meteo_mots = ["météo", "pluie", "arroser", "semaine", "ndaw"]
    if any(k in msg for k in meteo_mots):
        result = TOOL_FUNCTIONS["get_weather"](location=location.lower())
        results.append(f"MÉTÉO:\n{json.dumps(result, ensure_ascii=False)}")

    return results


# ---------------------------------------------------------------------------
# Appel LLM via serveur d'inférence
# ---------------------------------------------------------------------------
def call_llm(prompt: str) -> str:
    try:
        r = requests.post(INFER_URL, json={"prompt": prompt}, timeout=120)
        return r.json().get("response", "Erreur inférence")
    except Exception as e:
        return f"Erreur : {str(e)}"


# ---------------------------------------------------------------------------
# Synthèse vocale
# ---------------------------------------------------------------------------
_WOLOF_MARKERS = {"jëfandikoo","dafa","tàkk","ndox","garab","ci","bi","yi"}

# URL du Space HuggingFace Wolof TTS
WOLOF_TTS_URL = "https://ndaosaer-wolof-tts.hf.space/predict"

def text_to_speech(text: str, language: str = "fr") -> str | None:
    """
    Synthese vocale via gTTS.
    Français et Wolof utilisent le moteur français — meilleur fallback
    disponible pour le Wolof en attendant le déploiement GPU du Space
    GalsenAI xTTS v2 (huggingface.co/spaces/ndaosaer/wolof-tts).
    """
    try:
        tts = gTTS(text=text[:500], lang="fr", slow=False)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.save(tmp.name)
        with open(tmp.name, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")
        os.unlink(tmp.name)
        return audio_b64
    except Exception as e:
        print(f"Erreur TTS : {e}")
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

    response = None

    # ── Si image → CNN en priorité ───────────────────────────────────
    if image:
        try:
            img_bytes = base64.b64decode(image)
            img = PILImage.open(io.BytesIO(img_bytes))
            img.thumbnail((800, 800))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            image_b64_processed = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception as e:
            return jsonify({"error": f"Image invalide : {str(e)}"})

        response = diagnose_image(image_b64_processed, language)

    # ── Si pas d'image ou CNN n'a pas répondu → LLM ─────────────────
    if not response:
        lang_label   = "Français" if language == "fr" else "Wolof"
        default_msg  = "Décris ce que tu vois sur cette photo."
        full_msg     = f"[Zone: {location} | Langue: {lang_label}]\n{message or default_msg}"

        tool_results = run_tools(message or "", location, language)
        if tool_results:
            context  = "\n\n".join(tool_results)
            full_msg = f"{full_msg}\n\n=== Données ===\n{context}\n=== Fin ==="

        response = call_llm(full_msg)

    # ── Audio ─────────────────────────────────────────────────────────
    audio = text_to_speech(response, language=language)
    return jsonify({"response": response, "audio": audio})


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("FarmSense v2 — CNN + Gemma4")
    print(f"CNN : {'chargé' if model_cnn else 'non disponible'}")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
