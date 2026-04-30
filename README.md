# 🌾 FarmSense — Assistant Agricole Intelligent pour le Sahel

**Gemma 4 Good Hackathon | Kaggle × Google DeepMind**
**Piste : Global Resilience — Digital Divide & Agricultural Access**

> Mamadou est agriculteur à Kaolack. Ses feuilles de mil jaunissent depuis le bas.
> Il envoie une description à FarmSense.
> En quelques secondes, en Wolof, il reçoit : le diagnostic (Mildiou du mil),
> la cause, les 3 actions à faire aujourd'hui, et la météo de sa zone.
> Sans agronome. Sans connexion permanente. Dans sa langue maternelle.

---

## 🎯 Le problème

Au Sénégal, plus de 60% de la population active travaille dans l'agriculture.
Les petits agriculteurs perdent chaque année entre 30% et 50% de leurs récoltes
à cause de maladies non diagnostiquées à temps.

- 1 agronome pour ~3 000 agriculteurs (ISRA, 2023)
- Connectivité limitée dans les zones rurales
- Barrière linguistique : la majorité parle Wolof, pas Français
- Délai fatal : l'ergot du sorgho détruit une récolte en 48h si non traité

FarmSense s'attaque directement à ces 4 obstacles.

---

## 💡 La solution

FarmSense est un assistant agricole multimodal basé sur **Gemma 4 fine-tuné**
spécifiquement pour les cultures et maladies du Sénégal et du Sahel.

| Capacité | Usage dans FarmSense |
|---|---|
| Gemma 4 fine-tuné (QLoRA) | Modèle spécialisé agriculture Sénégal/Wolof |
| Base phytosanitaire offline | 20 maladies, 11 cultures, Français + Wolof |
| Météo temps réel | Open-Meteo, alertes agricoles automatiques |
| Prix du marché | Données FCFA par culture et par région |
| Synthèse vocale | Réponses audio en Français et Wolof |

---

## 🤖 Modèle Fine-tuné

Le modèle **FarmSense-Gemma4** est disponible sur HuggingFace :
**https://huggingface.co/ndaosaer/farmsense-gemma4-v2**

### Méthodologie du fine-tuning

- **Modèle de base** : Gemma 4 E4B (unsloth/gemma-4-E4B-it)
- **Méthode** : QLoRA 4-bit avec Unsloth (2x plus rapide)
- **Dataset** : 133 exemples conversationnels originaux
- **Epochs** : 8 — learning rate : 1e-4
- **Loss finale** : 0.95 (derniers steps)
- **Durée** : ~18 minutes sur GPU T4

### Dataset original

133 exemples couvrant :
- Diagnostics de 20 maladies agricoles (Français + Wolof)
- Questions météo avec alertes agricoles
- Prix du marché avec conseils de vente
- Conversations multi-tours (suivi traitement)
- Gestion post-récolte et stockage
- Cultures maraîchères

---

## 🌱 Base de données phytosanitaire — Contribution originale

La base `data/diseases.json` est une **contribution originale open-source**.
À notre connaissance, aucune base similaire n'existe en accès libre avec :

- **20 maladies** spécifiques au Sénégal et au Sahel
- **11 cultures** : mil, sorgho, maïs, riz, arachide, niébé, manioc, tomate, oignon, gombo, pastèque
- **Français ET Wolof** pour chaque maladie
- **Niveau d'urgence en jours** pour prioriser l'action
- **Régions sénégalaises** concernées
- **Sources citées** : CABI, CIRAD, ISRA, FAO, INRAN, Agrisenegal

### Sources utilisées

| Source | Utilisation |
|---|---|
| CABI Crop Protection Compendium | Identification pathogènes, symptômes |
| CIRAD Agritrop | Publications Afrique tropicale |
| ISRA Sénégal | Variétés résistantes, contexte local |
| FAO Afrique de l'Ouest | Traitements recommandés |
| INRAN Niger 2024 | Maladies sorgho et mil sahélien |
| Agrisenegal.com | Maladies maraîchères Sénégal |

---

## 🗂️ Structure du projet

```
farmsense/
├── README.md
├── requirements.txt
├── DEMO_SCRIPT.md
│
├── app/
│   ├── app_flask.py          ← Serveur Flask principal
│   ├── tools.py              ← Météo, prix marché, base maladies
│   └── templates/
│       └── index.html        ← Interface web mobile-first
│
├── data/
│   └── diseases.json         ← Base phytosanitaire 20 maladies
│
├── training/
│   ├── generate_dataset.py       ← Dataset v1 (52 exemples)
│   ├── generate_dataset_v2.py    ← Dataset v2 (52 exemples)
│   ├── generate_dataset_v3.py    ← Dataset v3 corrections (29 exemples)
│   └── farmsense_dataset_v4.jsonl ← Dataset final (133 exemples)
│
└── notebooks/
    ├── farmsense_kaggle.ipynb        ← Lancement app (4 cellules)
    └── farmsense_finetune_v2.ipynb   ← Fine-tuning Unsloth
```

---

## 🚀 Lancer le projet

### Sur Kaggle (recommandé)

1. Ouvrir `notebooks/farmsense_kaggle.ipynb`
2. Activer **GPU T4** dans les paramètres
3. Remplacer les tokens HuggingFace et ngrok
4. Exécuter les **4 cellules dans l'ordre**
5. Le lien public apparaît à la fin de la cellule 4

### En local

```bash
# 1. Installer Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma4:e4b

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer
cd app
python app_flask.py
```

### Relancer le fine-tuning

```bash
# Sur Kaggle avec GPU T4
# Ouvrir notebooks/farmsense_finetune_v2.ipynb
# Exécuter cellules 1 → 2 → 3 → 4
```

---

## 🌍 Impact

### Cible directe
- **700 000+** exploitations agricoles familiales au Sénégal
- Zones sans accès agronome : bassin arachidier, Casamance, vallée du Fleuve

### Pourquoi ça fonctionne

**Offline-first** — La base de maladies est embarquée localement.
Sans réseau, le diagnostic fonctionne. Météo et prix enrichissent
la réponse quand la connexion est disponible.

**Wolof** — Langue maternelle de ~40% des Sénégalais.
Comprendre un conseil dans sa langue maternelle, c'est la différence
entre agir à temps ou perdre sa récolte.

**Voix** — Pour les agriculteurs peu alphabétisés, l'audio est essentiel.

**Réponses courtes** — 8 lignes maximum, lisible sur écran de téléphone
en plein soleil au champ.

### Extensibilité
- Autres langues : Pulaar, Sérère, Mandingue
- Autres pays : Mali, Burkina Faso, Niger, Tchad
- Enrichissement dataset : par agents terrain non-développeurs

---

## 📊 Alignement critères hackathon

| Critère | Poids | Réponse FarmSense |
|---|---|---|
| Innovation | 30% | Gemma 4 fine-tuné agriculture Sénégal/Wolof — premier modèle de ce type open-source |
| Impact | 30% | 700k+ agriculteurs cibles, problème documenté de survie économique |
| Exécution technique | 25% | Fine-tuning QLoRA + base offline + météo + voix + interface mobile |
| Accessibilité | 15% | Offline, voix, Wolof, smartphone basique suffisant |

---

## 🔮 Améliorations prévues (v2)

- **Dataset multimodal** : intégration de PlantVillage (54 000 images) pour fine-tuner la vision
- **Google Cloud TTS** : synthèse vocale Wolof native
- **Support Pulaar et Sérère** : 3ème et 4ème langues du Sénégal
- **Application Android** : déploiement 100% hors connexion
- **Partenariat ISRA** : validation scientifique et enrichissement de la base

---

## ⚠️ Limitations connues

- La vision sur images non-agricoles peut donner des résultats imprécis.
  Le modèle est optimisé pour les descriptions textuelles et les photos de cultures.
  Une version multimodale avec dataset d'images est en développement (PlantVillage).
- Les prix du marché sont indicatifs (mise à jour manuelle).
- La synthèse vocale Wolof utilise une approximation phonétique (hausa).

---

*"La technologie la plus puissante est celle qui atteint ceux qui en ont le plus besoin."*
