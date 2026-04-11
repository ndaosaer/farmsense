"""
FarmSense — app.py
==================
Point d'entrée principal de l'application.

Lance l'interface Gradio et orchestre les appels à Gemma 4 via Ollama.
Gemma 4 reçoit le message + la photo, décide quels outils appeler,
et produit une réponse en Français ou Wolof avec synthèse vocale.

Pour lancer localement :
    python app.py

Pour lancer depuis Kaggle :
    Voir notebooks/farmsense_kaggle.ipynb
"""

import base64
import io
import json
import os
import tempfile
import traceback

import gradio as gr
import requests
from PIL import Image as PILImage
from gtts import gTTS

from tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OLLAMA_URL  = os.getenv("OLLAMA_URL",  "http://localhost:11434")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma4:12b")

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
# Vérification de la connexion Ollama
# ---------------------------------------------------------------------------
def check_ollama() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Appel Gemma 4 avec boucle function calling
# ---------------------------------------------------------------------------
def call_gemma(messages: list, image_b64: str = None) -> str:
    """
    Envoie les messages à Gemma 4 via Ollama.
    Si une image est fournie, elle est incluse dans le dernier message utilisateur.
    Gère la boucle function calling : Gemma 4 peut appeler jusqu'à 3 outils
    avant de produire sa réponse finale.

    Paramètres
    ----------
    messages : list
        Historique de la conversation au format Ollama
    image_b64 : str, optional
        Image encodée en base64 (JPEG)

    Retourne
    --------
    str : réponse finale de Gemma 4
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

    # Boucle function calling (max 3 appels d'outils par réponse)
    for _ in range(3):
        payload = {
            "model":   GEMMA_MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "tools":   TOOL_DEFINITIONS,
            "stream":  False,
            "options": {"temperature": 0.3, "num_ctx": 8192}
        }

        r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        msg = r.json()["message"]

        # Pas d'appel d'outil → réponse finale, on sort de la boucle
        if not msg.get("tool_calls"):
            return msg["content"]

        # Il y a des appels d'outils → on les exécute
        messages.append({
            "role":       "assistant",
            "content":    msg.get("content", ""),
            "tool_calls": msg["tool_calls"]
        })

        for call in msg["tool_calls"]:
            fn_name = call["function"]["name"]
            fn_args = call["function"].get("arguments", {})

            # Les arguments peuvent arriver sous forme de chaîne JSON
            if isinstance(fn_args, str):
                fn_args = json.loads(fn_args)

            # Exécution de la fonction Python correspondante
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
# Synthèse vocale — Français et Wolof
# ---------------------------------------------------------------------------

# Mots wolof courants pour détecter automatiquement la langue du texte
_WOLOF_MARKERS = {
    "jëfandikoo", "dafa", "tàkk", "jaap", "ndox", "garab",
    "nit", "dëkk", "suba", "bëgg", "xamne", "wàcc", "jël",
    "topp", "neem", "yëgël", "ci", "bi", "yi", "bu"
}


def detect_language(text: str) -> str:
    """
    Détecte si le texte est en Wolof ou en Français.
    Retourne "wo" pour wolof, "fr" pour français.
    """
    words = set(text.lower().split())
    wolof_hits = len(words & _WOLOF_MARKERS)
    return "wo" if wolof_hits >= 2 else "fr"


def text_to_speech(text: str, language: str = "fr") -> str | None:
    """
    Génère un fichier audio MP3 depuis le texte de la réponse.

    Paramètres
    ----------
    text : str
        Texte à lire (tronqué à 500 caractères pour la vitesse)
    language : str
        "fr" pour français, "wo" pour wolof.
        Le Wolof n'étant pas supporté nativement par gTTS, on utilise
        le moteur hausa ("ha") qui est phonétiquement le plus proche
        des langues wolof/peul pour une prononciation acceptable.

    Retourne
    --------
    str : chemin du fichier MP3 temporaire, ou None si erreur
    """
    try:
        if language == "wo":
            # Vérifier si le texte est vraiment en wolof, sinon fallback français
            detected = detect_language(text)
            gtts_lang = "ha" if detected == "wo" else "fr"
        else:
            gtts_lang = "fr"

        tts = gTTS(text=text[:500], lang=gtts_lang, slow=False)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.save(tmp.name)
        return tmp.name

    except Exception:
        # Fallback : essayer en français si la langue choisie échoue
        try:
            tts = gTTS(text=text[:500], lang="fr", slow=False)
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tts.save(tmp.name)
            return tmp.name
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Logique d'un tour de conversation
# ---------------------------------------------------------------------------
def chat(user_message, image, language, location, history):
    """
    Gère un tour de conversation : reçoit le message et la photo,
    appelle Gemma 4, met à jour l'historique, génère la réponse audio.

    Paramètres (liés aux composants Gradio)
    ----------------------------------------
    user_message : str
    image        : PIL.Image ou None
    language     : "fr" ou "wo"
    location     : str (ville du Sénégal)
    history      : list [[user_msg, bot_msg], ...]

    Retourne
    --------
    (history mis à jour, input vidé, chemin audio)
    """
    if not user_message and image is None:
        return history, "", None

    # Enrichir le message avec le contexte de l'agriculteur
    lang_label = "Français" if language == "fr" else "Wolof"
    context    = f"[Zone : {location} | Langue : {lang_label}]"
    full_msg   = f"{context}\n{user_message or 'Analyse cette photo de ma plante.'}"

    # Construire l'historique au format Ollama
    messages = []
    for user_turn, bot_turn in history:
        messages.append({"role": "user",      "content": user_turn})
        messages.append({"role": "assistant", "content": bot_turn})
    messages.append({"role": "user", "content": full_msg})

    # Encoder l'image en base64 si fournie
    image_b64 = None
    if image is not None:
        if not isinstance(image, PILImage.Image):
            image = PILImage.open(image)
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Appel Gemma 4
    try:
        response = call_gemma(messages, image_b64)
    except requests.exceptions.ConnectionError:
        response = (
            "⚠️ Impossible de se connecter au modèle IA.\n\n"
            "Assurez-vous qu'Ollama est lancé :\n"
            f"  `ollama serve`\n\n"
            f"Et que le modèle est chargé :\n"
            f"  `ollama run {GEMMA_MODEL}`"
        )
    except Exception as e:
        response = f"Erreur inattendue : {str(e)}"

    history = history + [[user_message or "📷 Photo envoyée", response]]
    audio   = text_to_speech(response, language=language)

    return history, "", audio


# ---------------------------------------------------------------------------
# Construction de l'interface Gradio
# ---------------------------------------------------------------------------
def build_interface() -> gr.Blocks:
    ollama_ok  = check_ollama()
    status_txt = (
        f"✅ Gemma 4 prêt ({GEMMA_MODEL})"
        if ollama_ok
        else f"⚠️ Ollama non détecté — lancez : ollama run {GEMMA_MODEL}"
    )

    with gr.Blocks(
        title="FarmSense — Assistant Agricole",
        theme=gr.themes.Soft(primary_hue="green"),
        css="footer { display:none !important; }"
    ) as demo:

        # ── En-tête ──────────────────────────────────────────────────────
        gr.HTML("""
        <div style="text-align:center; padding:20px 0 8px;">
          <h1 style="font-size:2.2em; margin:0;">🌾 FarmSense</h1>
          <p style="color:#555; margin:6px 0 0; font-size:1.05em;">
            Assistant agricole intelligent pour les agriculteurs du Sénégal et du Sahel<br>
            <em>Gemma 4 — multimodal, function calling, offline-ready</em>
          </p>
        </div>
        """)
        gr.HTML(
            f'<p style="text-align:center; font-size:.9em; color:#777; margin:0 0 12px;">'
            f'{status_txt}</p>'
        )

        with gr.Row():

            # ── Colonne gauche : paramètres ───────────────────────────────
            with gr.Column(scale=1, min_width=260):
                gr.Markdown("### ⚙️ Paramètres")

                language = gr.Radio(
                    choices=[("🇫🇷 Français", "fr"), ("🇸🇳 Wolof", "wo")],
                    value="fr",
                    label="Langue / Làkk"
                )

                location = gr.Dropdown(
                    choices=[
                        "Dakar", "Thiès", "Kaolack", "Ziguinchor",
                        "Saint-Louis", "Tambacounda", "Kolda",
                        "Louga", "Fatick", "Kaffrine"
                    ],
                    value="Kaolack",
                    label="🗺️ Votre zone"
                )

                image_input = gr.Image(
                    type="pil",
                    label="📷 Photo de votre plante (optionnelle)",
                    height=200
                )

                gr.Markdown("---\n### Exemples / Xam-xam")
                examples_fr = [
                    "Mes feuilles de mil jaunissent depuis le bas",
                    "Taches brunes sur mes feuilles d'arachide",
                    "Quelle est la météo cette semaine ?",
                    "Quel est le prix actuel de l'arachide ?",
                ]
                examples_wo = [
                    "Feuilles yu mil dafa set ci jaambur",
                    "Am na taches yu ñuul ci feuilles yu gerte",
                ]
                for ex in examples_fr + examples_wo:
                    gr.Button(ex, size="sm", variant="secondary").click(
                        fn=lambda msg=ex: msg,
                        outputs=gr.Textbox(visible=False)
                    )

            # ── Colonne droite : chatbot ──────────────────────────────────
            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="FarmSense",
                    height=430,
                    avatar_images=(None, "🌾"),
                    show_copy_button=True,
                    value=[[
                        None,
                        "Bonjour ! Je suis FarmSense, votre assistant agricole.\n\n"
                        "Dites-moi votre problème ou envoyez une photo de votre plante. "
                        "Je diagnostique les maladies, consulte la météo de votre zone, "
                        "et vous donne les prix du marché.\n\n"
                        "Je parle Français et Wolof.\n\n"
                        "Asalaa Maalekum ! Bind sa cosaan wala yónni foto ci sa garab."
                    ]]
                )

                with gr.Row():
                    user_input = gr.Textbox(
                        placeholder="Décrivez votre problème...",
                        label="",
                        scale=4,
                        autofocus=True
                    )
                    send_btn = gr.Button("Envoyer 📨", scale=1, variant="primary")

                audio_output = gr.Audio(
                    label="🔊 Réponse vocale",
                    autoplay=True
                )

                gr.Button("🗑️ Nouvelle conversation", size="sm", variant="secondary").click(
                    fn=lambda: (
                        [[None, "Nouvelle conversation démarrée. Comment puis-je vous aider ?"]],
                        "",
                        None
                    ),
                    outputs=[chatbot, user_input, audio_output]
                )

        # ── Événements ───────────────────────────────────────────────────
        inputs  = [user_input, image_input, language, location, chatbot]
        outputs = [chatbot, user_input, audio_output]

        send_btn.click(fn=chat, inputs=inputs, outputs=outputs)
        user_input.submit(fn=chat, inputs=inputs, outputs=outputs)

    return demo


# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    demo = build_interface()
    demo.launch(
        share=True,           # Génère un lien public — indispensable sur Kaggle
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True
    )
