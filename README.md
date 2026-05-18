# FarmSense: Agricultural Intelligence Assistant for the Sahel

**Gemma 4 Good Hackathon | Kaggle x Google DeepMind**
**Track: Global Resilience, Digital Divide and Agricultural Access**

---

## Overview

FarmSense is an intelligent agricultural assistant designed for smallholder farmers in Senegal and the Sahel region. It combines a fine-tuned Gemma 4 language model with a high-precision CNN image classifier to provide accurate crop disease diagnosis, weather alerts, and market price guidance in both French and Wolof.

The system is designed to operate in low-connectivity environments, with an offline disease database and a lightweight architecture that runs on a standard smartphone browser.

---

## The Problem

In Senegal, over 60 percent of the active population works in agriculture. Smallholder farmers lose between 30 and 50 percent of their harvest each year due to diseases that are not diagnosed in time.

The obstacles are concrete and well-documented:

- 1 agronomist for approximately 3,000 farmers (ISRA, 2023)
- Limited or no connectivity in rural Sahel areas
- Language barrier: the majority of farmers speak Wolof, not French
- Critical delay: diseases like sorghum ergot or cassava mosaic can destroy an entire harvest within 48 hours if untreated

FarmSense addresses all four obstacles simultaneously.

---

## Architecture

FarmSense uses a hybrid architecture combining two specialized models:

**Image diagnosis pipeline:**
The user sends a photo of a sick plant. An EfficientNet-B0 CNN classifier trained on 34,525 images identifies the disease with 99.4 percent accuracy. The result is mapped to a structured FarmSense response with diagnosis, cause, numbered actions, and an immediate action.

**Text and voice pipeline:**
The user describes their problem in text. A fine-tuned Gemma 4 E4B model generates a structured response in French or Wolof, enriched with real-time weather data from Open-Meteo and local market prices in FCFA.

**Why a hybrid architecture:**
Native multimodal fine-tuning of Gemma 4 with images is still experimental in the Unsloth framework. Rather than producing imprecise visual diagnoses, we trained a dedicated EfficientNet-B0 classifier that achieves near-perfect accuracy on the crop diseases covered. Gemma 4 handles all natural language tasks. The two models are complementary and each operates at its optimal capability.

---

## CNN Image Classifier

**Model:** EfficientNet-B0 fine-tuned on PlantVillage and Groundnut Leaf Disease datasets

**Training data:**

| Dataset | Cultures | Images | Source |
|---|---|---|---|
| PlantVillage | Tomato, Corn, Potato | 22,164 | kaggle.com/abdallahalidev |
| Groundnut Leaf Disease | Groundnut (Peanut) | 10,361 | kaggle.com/warcoder |
| Total | 4 crops | 32,525 | 20 disease classes |

**Training results:**

| Epoch | Train Accuracy | Validation Accuracy |
|---|---|---|
| 1 | 84.1% | 93.0% |
| 4 | 97.7% | 98.9% |
| 8 | 99.3% | 99.4% |

**Final validation accuracy: 99.4%**

**Classes covered (20):**

Tomato: Bacterial Spot, Early Blight, Late Blight, Leaf Mold, Septoria Leaf Spot, Spider Mites, Target Spot, Yellow Leaf Curl Virus, Mosaic Virus, Healthy

Corn (Maize): Common Rust, Northern Leaf Blight, Gray Leaf Spot, Healthy

Groundnut (Peanut): Early Leaf Spot, Late Leaf Spot, Rust, Early Rust, Nutrition Deficiency, Healthy

**Model published:** https://huggingface.co/ndaosaer/farmsense-cnn

---

## Fine-tuned Language Model

**Base model:** Gemma 4 E4B (unsloth/gemma-4-E4B-it)

**Method:** QLoRA 4-bit fine-tuning with Unsloth

**Dataset v4 (133 examples):**

| Category | French | Wolof | Total |
|---|---|---|---|
| Disease diagnosis | 20 | 17 | 37 |
| Pests and insects | 8 | 0 | 8 |
| Seed varieties ISRA | 5 | 4 | 9 |
| Post-harvest storage | 4 | 5 | 9 |
| Market prices | 6 | 7 | 13 |
| Weather alerts | 5 | 3 | 8 |
| Market gardening | 5 | 0 | 5 |
| Emergency cases | 4 | 0 | 4 |
| Multi-turn conversations | 4 | 3 | 7 |
| General agriculture | 7 | 3 | 10 |
| Corrected format examples | 6 | 10 | 16 |
| Photo non-agricultural | 4 | 0 | 4 |
| Contextual follow-up | 6 | 3 | 9 |
| Total | 90 | 55 | 133 |

**Training parameters:**

- Epochs: 8
- Learning rate: 1e-4
- LoRA rank: 16
- Batch size: 1 with gradient accumulation steps 8
- Scheduler: cosine
- Loss final steps: 0.0015
- Training duration: approximately 18 minutes on GPU T4

**Model published:** https://huggingface.co/ndaosaer/farmsense-gemma4-v2

---

## Disease Database

The file `data/diseases.json` is an original contribution of this project. To our knowledge, no publicly available phytosanitary database combines all of the following:

- 20 diseases specific to Senegal and the Sahel
- 11 crops covered: millet, sorghum, corn, rice, peanut, cowpea, cassava, tomato, onion, okra, watermelon
- Complete data in both French and Wolof for each disease
- Urgency level in days to prioritize action
- Senegalese regions affected per pathology
- Cited scientific sources for each entry

**Sources:**

| Source | Usage |
|---|---|
| CABI Crop Protection Compendium (cabi.org/cpc) | Pathogen identification, symptoms, distribution |
| CIRAD Agritrop (agritrop.cirad.fr) | Tropical Africa and Sahel publications |
| ISRA Senegal (isra.sn) | Resistant varieties, local context |
| FAO West Africa | Recommended treatments, emergency protocols |
| INRAN Niger 2024 | Sorghum and millet diseases, Sahelian zone |
| Agrisenegal.com | Market gardening diseases, Senegal context |

The database was compiled manually. Each disease entry was verified against at least one primary scientific source. Data was not scraped automatically. The Wolof translations were developed with the support of linguistic resources and adapted to the oral agricultural vocabulary used in the field.

This database is published as an open-source contribution under the MIT license and can be enriched by field agents without developer skills.

---

## Project Structure

Gemma 4 fine-tuned agricultural assistant for Senegal and the Sahel. Crop disease diagnosis in French and Wolof via CNN classifier (99.4% accuracy) and fine-tuned language model.
Offline-first, mobile-first.


```
farmsense/
    README.md
    requirements.txt
    DEMO_SCRIPT.md
    app/
        app_flask.py              Flask server with CNN and LLM integration
        tools.py                  Weather, market prices, disease database tools
        templates/
            index.html            Mobile-first web interface
    data/
        diseases.json             Phytosanitary database, 20 diseases, French and Wolof
    training/
        generate_dataset.py       Dataset v1, 52 examples
        generate_dataset_v2.py    Dataset v2, 52 examples
        generate_dataset_v3.py    Dataset v3 corrections, 29 examples
        farmsense_dataset_v4.jsonl  Final dataset, 133 examples
    notebooks/
        farmsense_kaggle.ipynb       Launch notebook, 4 cells
        farmsense_finetune_v2.ipynb  Fine-tuning notebook, Unsloth QLoRA
```

---

## Technical Stack

| Component | Technology | Role |
|---|---|---|
| Image classifier | EfficientNet-B0, PyTorch | Disease diagnosis from photos |
| Language model | Gemma 4 E4B, fine-tuned | French and Wolof responses |
| Fine-tuning framework | Unsloth QLoRA 4-bit | Efficient fine-tuning on T4 GPU |
| Web interface | Flask, HTML, CSS, JavaScript | Mobile-first user interface |
| Public tunnel | ngrok | Public URL from Kaggle environment |
| Weather data | Open-Meteo API | Free, no API key, West Africa coverage |
| Text-to-speech | gTTS | Audio responses in French and Wolof |
| Disease database | JSON, offline | Works without internet connection |

---

## Running the Project

### On Kaggle (recommended for demonstration)

1. Open `notebooks/farmsense_kaggle.ipynb`
2. Enable GPU T4 in the notebook settings
3. Replace HuggingFace and ngrok tokens in cells 2 and 4
4. Execute cells 1 through 4 in order
5. The public link appears at the end of cell 4

### Local installation

```bash
# Install Ollama for local LLM serving
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma4:e4b

# Install Python dependencies
pip install -r requirements.txt

# Launch FarmSense
cd app
python app_flask.py
```

---

## Impact

**Direct target population:**
700,000 or more smallholder farms in Senegal. Priority zones without agronomist access: the peanut basin, Casamance, the Senegal River valley.

**Why this works in context:**

Offline-first design: The disease database is embedded locally. Even without a 4G network, diagnosis works. Weather and market prices enrich the response when a connection is available, but are never blocking.

Language accessibility: Wolof is the mother tongue of approximately 40 percent of Senegalese citizens and the national lingua franca. Receiving agricultural advice in one's mother tongue is not a comfort; it is the difference between understanding and acting in time.

Voice output: For farmers with limited literacy, automatic audio output is essential. The text displays for those who can read; the audio plays for everyone.

Response length: Maximum 8 lines, plain text, no formatting. Designed to be read on a phone screen in direct sunlight in the field.

**Scalability:**
Other languages: Pulaar, Serer, Mandinka, same architecture, new data fields
Other countries: Mali, Burkina Faso, Niger, Chad, same crops, same disease base
Price updates: editable by a field agent in the JSON file, no developer required
New diseases: a new JSON entry by an agronomist, no technical skills required

---

## Hackathon Criteria Alignment

| Criterion | Weight | FarmSense Response |
|---|---|---|
| Innovation | 30% | CNN classifier at 99.4% accuracy trained on African crops; original bilingual phytosanitary database; first agricultural assistant with Wolof support published open-source |
| Impact | 30% | 700,000+ target farmers; documented economic survival problem; deployable immediately in the field |
| Technical execution | 25% | EfficientNet-B0 vision + Gemma 4 fine-tuned language + offline-first architecture + voice synthesis |
| Accessibility | 15% | Offline capable, voice output, Wolof language, mobile-first, works on basic smartphone |

---

## Roadmap Version 2

- Google Cloud Text-to-Speech integration for native Wolof voice synthesis
- Pulaar and Serer language support (3rd and 4th languages of Senegal)
- Expansion of the CNN classifier to millet, sorghum, and cassava using newly collected field datasets
- Lightweight Android application for fully offline deployment
- Partnership with ISRA for scientific validation and database enrichment
- Extension to the five Sahel countries most affected by food insecurity

---

## Known Limitations

The CNN classifier covers tomato, corn, and peanut diseases. Millet, sorghum, cassava, rice, and cowpea are currently handled by text description only, as no public image datasets exist for these Sahelian crops. Field image collection for these crops is planned for version 2.

The Wolof voice synthesis uses a phonetic approximation through the Hausa engine in gTTS. Native Wolof text-to-speech via Google Cloud TTS is planned for version 2.

Market prices are indicative values updated manually. Integration with official ANSD market price feeds is planned.

---

## Citation

If you use the FarmSense disease database or dataset in your work, please cite:

```
FarmSense Agricultural Database, 2026
Bilingual phytosanitary database for Senegal and the Sahel (French and Wolof)
Sources: CABI CPC, CIRAD Agritrop, ISRA Senegal, FAO West Africa, INRAN Niger
Available at: https://github.com/ndaosaer/farmsense
```

---

## Wolof Voice Synthesis: Architecture and Roadmap

### Current implementation

The current version uses gTTS (Google Text-to-Speech) with the French phonetic engine as an approximation for Wolof audio output. This produces intelligible audio but with French pronunciation patterns rather than native Wolof phonetics.

### GalsenAI xTTS v2 Wolof: Integrated and Pending GPU Deployment

A native Wolof text-to-speech system has been fully integrated into the FarmSense architecture. The implementation uses the GalsenAI xTTS v2 Wolof model, developed by the GalsenAI community (github.com/Galsenaicommunity), which is the only open-source neural TTS model trained specifically on Wolof speech data.

The integration is complete and functional:

- Model files are published at huggingface.co/ndaosaer/wolof-tts-model (8.1 GB total)
- A HuggingFace Space is deployed at huggingface.co/spaces/ndaosaer/wolof-tts exposing a REST API endpoint POST /predict
- The Space accepts Wolof text and returns a WAV audio file
- The FarmSense Flask server is architected to call this endpoint when language is set to Wolof
- All xTTS language patches required to support the Wolof language code have been implemented and validated

The API returns correct audio when called with sufficient timeout. The blocking issue is inference speed on CPU hardware: the 5.6 GB GPT fine-tuned checkpoint requires approximately 300 seconds per inference on the free CPU tier of HuggingFace Spaces, which is not acceptable for real-time agricultural assistance.

### What is needed for production

Deploying the HuggingFace Space on an Nvidia T4 GPU instance reduces inference time from 300 seconds to approximately 2 to 3 seconds per response. This is the only remaining step to enable native Wolof voice synthesis in production.

The model, the Space, the API, and the FarmSense integration code are all ready. Only the GPU compute resource is missing.

### Technical details of the xTTS integration

The GalsenAI xTTS v2 model does not natively register Wolof as a supported language in the TTS library. The following patches were developed and validated to enable Wolof inference:

- Added "wo" to config.languages to pass the configuration validation
- Added "wo" to tokenizer.char_limits with the French character limit (273 characters) to pass the sentence splitting validation
- Patched VoiceBpeTokenizer.preprocess_text to redirect language code "wo" to the French preprocessor, which handles the Latin alphabet used by Wolof

These patches are implemented in the HuggingFace Space app.py and do not modify the underlying model weights.

### Data attribution

The GalsenAI xTTS v2 Wolof checkpoint was trained by the GalsenAI community on Wolof speech data recorded by native speakers. The voice reference used in FarmSense (anta_sample.wav) is the sample provided with the original checkpoint. Full attribution to GalsenAI and the original contributors.

