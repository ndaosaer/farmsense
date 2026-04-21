"""
FarmSense — Générateur de dataset de fine-tuning
=================================================
Génère ~300 exemples de conversations agricoles Sénégal/Sahel
en Français et en Wolof pour fine-tuner Gemma 4.

Format de sortie : JSONL (une ligne JSON par exemple)
Compatible avec Unsloth QLoRA fine-tuning.
"""

import json
import random

random.seed(42)

# ---------------------------------------------------------------------------
# Exemples Français — Diagnostics de maladies
# ---------------------------------------------------------------------------
EXEMPLES_MALADIES_FR = [

    # Mildiou du mil
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nMes feuilles de mil jaunissent depuis le bas, il y a une poudre grise en dessous.",
        "response": "C'est le Mildiou du mil (Sclerospora graminicola).\nC'est un champignon qui se développe quand il fait chaud et humide.\n1. Retire et brûle immédiatement toutes les feuilles jaunes.\n2. Applique du Métalaxyl (Ridomil) 2g par litre d'eau sur les feuilles restantes.\n3. Arrose uniquement le matin, jamais le soir.\n4. Espace bien tes plants pour que l'air circule.\nAction immédiate : Brûle toutes les feuilles jaunes aujourd'hui avant midi."
    },
    {
        "instruction": "[Zone: Thiès | Langue: Français]\nMon mil a des feuilles déformées et enroulées avec des taches jaunes.",
        "response": "C'est probablement le Mildiou du mil.\nLe champignon Sclerospora graminicola attaque quand l'humidité est forte.\n1. Enlève toutes les feuilles malades et brûle-les loin du champ.\n2. Traite avec Métalaxyl 2g/L dès aujourd'hui.\n3. Évite d'arroser le soir.\n4. L'année prochaine, utilise des semences certifiées traitées.\nAction immédiate : Retire toutes les feuilles déformées maintenant."
    },
    {
        "instruction": "[Zone: Diourbel | Langue: Français]\nMes épis de mil sont malformés et stériles, les feuilles sont jaunes.",
        "response": "C'est le Mildiou du mil à un stade avancé.\nLe champignon a attaqué avant la floraison, ce qui explique les épis vides.\n1. Retire et brûle tous les épis et feuilles malades.\n2. Applique du Métalaxyl 2g/L sur les plants encore sains.\n3. Pour la prochaine saison, choisis des variétés résistantes de l'ISRA.\n4. Pratique la rotation avec des légumineuses l'année prochaine.\nAction immédiate : Brûle les épis malades pour stopper la propagation."
    },

    # Charbon du mil
    {
        "instruction": "[Zone: Louga | Langue: Français]\nMes épis de mil ont des masses noires qui font de la poudre noire au vent.",
        "response": "C'est le Charbon du mil (Tolyposporium penicillariae).\nLe champignon remplace les grains par des spores noires.\n1. Détruis immédiatement ces épis — ne les laisse pas sécher sur pied.\n2. Ne récupère JAMAIS ces grains comme semences — ils contamineraient tout.\n3. Pour la prochaine saison, traite tes semences avec du Thirame 3g/kg.\n4. Change de parcelle — pratique la rotation.\nAction immédiate : Arrache et brûle tous les épis noirs aujourd'hui."
    },

    # Ergot du sorgho
    {
        "instruction": "[Zone: Tambacounda | Langue: Français]\nMon sorgho a un liquide collant sucré sur la panicule et ça sent la fermentation.",
        "response": "URGENT : C'est l'Ergot du sorgho (Claviceps africana).\nCes grains sont DANGEREUX — toxiques pour les humains et les animaux.\n1. N'utilise JAMAIS ces grains — ne les mange pas et ne les donne pas aux animaux.\n2. Arrache et brûle toutes les panicules atteintes aujourd'hui même.\n3. Traite les plants voisins sains avec Propiconazole 0,5mL/L en préventif.\n4. Préviens l'agent agricole local.\nAction immédiate : Arrache et brûle toutes les panicules contaminées MAINTENANT."
    },
    {
        "instruction": "[Zone: Kolda | Langue: Français]\nMes panicules de sorgho ont des masses roses violacées à la place des grains.",
        "response": "URGENT : C'est l'Ergot du sorgho — situation très grave.\nLes masses roses sont toxiques pour toute la famille et le bétail.\n1. Ne touche pas ces grains sans gants si possible.\n2. Brûle immédiatement toutes les panicules atteintes.\n3. Traite les plants encore sains avec Propiconazole 0,5mL/L.\n4. Informe immédiatement l'agent agricole de ta zone.\nAction immédiate : Brûle toutes les panicules roses — c'est une urgence sanitaire."
    },

    # Striure du maïs
    {
        "instruction": "[Zone: Tambacounda | Langue: Français]\nMes feuilles de maïs ont des rayures jaunes et vertes alternées et les plants sont petits.",
        "response": "C'est la Striure du maïs (Maize Streak Virus).\nCe virus est transmis par les cicadelles — de petits insectes sauteurs.\n1. Il n'y a pas de traitement direct contre le virus — il faut combattre les cicadelles.\n2. Traite contre les cicadelles avec Imidaclopride 0,5mL/L dès aujourd'hui.\n3. Arrache et brûle les plants très touchés pour éviter la propagation.\n4. La prochaine saison, utilise des variétés résistantes MSV recommandées par l'ISRA.\nAction immédiate : Applique l'insecticide contre les cicadelles aujourd'hui."
    },

    # Cercosporiose arachide
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nMes feuilles d'arachide ont de petites taches brunes cerclées de jaune sur les deux faces.",
        "response": "C'est la Cercosporiose de l'arachide (Cercospora arachidicola).\nC'est un champignon très commun dans le Bassin arachidier.\n1. Traite avec Chlorothalonil (Daconil) 2,5g/L dès maintenant.\n2. Répète le traitement toutes les 2 semaines.\n3. Ramasse et brûle toutes les feuilles tombées au sol.\n4. Assure une bonne circulation d'air en désherban entre les rangs.\nAction immédiate : Applique le traitement Chlorothalonil aujourd'hui."
    },
    {
        "instruction": "[Zone: Fatick | Langue: Français]\nMes arachides perdent leurs feuilles prématurément, il y a des taches circulaires.",
        "response": "C'est la Cercosporiose de l'arachide à un stade avancé.\nLa défoliation précoce réduit sérieusement le rendement.\n1. Commence le traitement au Chlorothalonil 2,5g/L immédiatement.\n2. Continue les traitements toutes les 2 semaines jusqu'à 6 semaines avant récolte.\n3. Ramasse toutes les feuilles tombées et brûle-les.\n4. La prochaine saison, utilise des variétés résistantes ISRA comme Fleur11.\nAction immédiate : Traite au Chlorothalonil aujourd'hui sans attendre."
    },

    # Rouille arachide
    {
        "instruction": "[Zone: Ziguinchor | Langue: Français]\nSous mes feuilles d'arachide il y a des pustules orangées, une poudre orange se détache.",
        "response": "C'est la Rouille de l'arachide (Puccinia arachidis).\nLes spores orange se dispersent par le vent entre les parcelles.\n1. Traite avec Propiconazole 0,5mL/L ou Mancozèbe 2g/L immédiatement.\n2. Répète le traitement toutes les 3 semaines si le temps est humide.\n3. Arrose uniquement au pied des plantes, jamais par aspersion.\n4. La prochaine saison, commence les traitements préventifs 45 jours après le semis.\nAction immédiate : Applique le fongicide aujourd'hui."
    },

    # Alternariose tomate
    {
        "instruction": "[Zone: Dakar | Langue: Français]\nMes tomates ont des taches brunes en forme de cible avec des cercles concentriques.",
        "response": "C'est l'Alternariose de la tomate (Alternaria solani).\nCe champignon attaque d'abord les feuilles du bas.\n1. Retire immédiatement toutes les feuilles touchées et brûle-les.\n2. Traite au Mancozèbe (Dithane) 2g/L dès aujourd'hui.\n3. Paille le sol autour des tomates pour éviter les éclaboussures.\n4. Arrose uniquement à la base, jamais sur les feuilles.\nAction immédiate : Retire toutes les feuilles avec taches et applique le traitement."
    },
    {
        "instruction": "[Zone: Saint-Louis | Langue: Français]\nMes plants de tomate ont des taches noires enfoncées sur les fruits et les feuilles du bas sont mortes.",
        "response": "C'est l'Alternariose de la tomate à un stade avancé.\nLe champignon a atteint les fruits — agis vite pour sauver le reste.\n1. Enlève toutes les feuilles malades et les fruits touchés.\n2. Traite avec Mancozèbe 2g/L immédiatement et toutes les semaines.\n3. Assure-toi d'arroser uniquement au pied, jamais sur le feuillage.\n4. Installle un paillage pour protéger contre les éclaboussures de sol.\nAction immédiate : Traite avec Mancozèbe aujourd'hui et taille les parties malades."
    },

    # Flétrissement bactérien tomate
    {
        "instruction": "[Zone: Niayes | Langue: Français]\nMa tomate s'est complètement fanée d'un coup, les feuilles sont encore vertes mais la plante est morte.",
        "response": "C'est le Flétrissement bactérien (Ralstonia solanacearum).\nCette bactérie du sol n'a pas de traitement curatif efficace.\n1. Arrache immédiatement le plant malade et brûle-le loin du champ.\n2. Désinfecte tes outils avec de l'eau de javel diluée à 10%.\n3. Ne replante pas de tomates sur cette parcelle pendant 3 à 4 ans minimum.\n4. Améliore le drainage de ton sol — la bactérie adore les sols engorgés.\nAction immédiate : Arrache et brûle le plant malade maintenant."
    },

    # Mosaïque manioc
    {
        "instruction": "[Zone: Ziguinchor | Langue: Français]\nMes feuilles de manioc sont jaunes et vertes en mosaïque et les plants sont très petits.",
        "response": "URGENT : C'est la Mosaïque du manioc (African Cassava Mosaic Virus).\nCe virus se propage très vite par les mouches blanches.\n1. Arrache et brûle IMMÉDIATEMENT tous les plants malades.\n2. Traite contre les mouches blanches avec Imidaclopride 0,5mL/L sur les plants voisins.\n3. Replante UNIQUEMENT avec des boutures certifiées saines — jamais de boutures de plants malades.\n4. Surveille les plants voisins chaque jour cette semaine.\nAction immédiate : Arrache tous les plants malades aujourd'hui — le virus se propage vite."
    },

    # Striga
    {
        "instruction": "[Zone: Kaffrine | Langue: Français]\nIl y a des plantes rouges qui poussent au pied de mon mil et mes plants sont tout petits.",
        "response": "C'est le Striga (herbe sorcière) — un parasite très dangereux.\nSes racines volent l'eau et les nutriments directement dans les racines de ton mil.\n1. Arrache le Striga AVANT qu'il fleurisse — une plante fait 50 000 graines.\n2. Ne le laisse JAMAIS monter en graines sur ton champ.\n3. La prochaine saison, sème du niébé ou de l'arachide — ils étouffent le Striga.\n4. Applique de l'urée en micro-dose 2g par poquet pour renforcer le mil.\nAction immédiate : Arrache tous les plants de Striga avant qu'ils fleurissent."
    },

    # Carence azote
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nTous mes plants de mil sont pâles et jaunes de façon uniforme, ils poussent très lentement.",
        "response": "C'est une Carence en azote.\nTon sol manque d'azote — souvent après des pluies fortes qui lessivent le sol.\n1. Apporte de l'urée (46-0-0) : 50kg par hectare en épandage latéral près des plants.\n2. Ou utilise du compost bien décomposé : 3 à 5 tonnes par hectare.\n3. Arrose après l'application pour dissoudre l'engrais dans le sol.\n4. Tu verras les plants reverdir en 5 à 7 jours.\nAction immédiate : Apporte de l'urée ou du compost autour des plants aujourd'hui."
    },
    {
        "instruction": "[Zone: Thiès | Langue: Français]\nMes tomates sont pâles, les vieilles feuilles du bas sont toutes jaunes.",
        "response": "C'est une Carence en azote sur tes tomates.\nLa plante puise l'azote des vieilles feuilles pour nourrir les nouvelles — c'est pour ça que le bas jaunit en premier.\n1. Apporte de l'urée 50kg/hectare ou du compost autour des plants.\n2. Arrose après pour dissoudre l'engrais.\n3. Évite de trop arroser — le lessivage aggrave la carence.\n4. Tu verras les résultats en 5 à 7 jours.\nAction immédiate : Apporte de l'engrais azoté ou du compost aujourd'hui."
    },

    # Aflatoxine arachide
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nMes arachides stockées ont une moisissure verdâtre et sentent le moisi.",
        "response": "DANGER SANTÉ : C'est l'Aflatoxine (Aspergillus flavus).\nCes arachides sont dangereuses — l'aflatoxine est cancérigène.\n1. Ne mange PAS ces arachides et ne les donne pas aux animaux.\n2. Jette tout le stock contaminé loin de ta maison.\n3. Nettoie et sèche le local de stockage avant de remettre du stock.\n4. La prochaine fois, sèche les gousses rapidement à moins de 8% d'humidité avant de stocker.\nAction immédiate : Retire et jette le stock contaminé — ne le consomme pas."
    },

    # Pyriculariose riz
    {
        "instruction": "[Zone: Saint-Louis | Langue: Français]\nMes feuilles de riz ont des taches en forme de losange grises avec un bord brun.",
        "response": "C'est la Pyriculariose du riz ou blast du riz (Magnaporthe oryzae).\nC'est une maladie très destructrice — agis vite.\n1. Traite immédiatement avec Tricyclazole (Beam) 0,6g/L.\n2. Applique 2 fois à 10 jours d'intervalle.\n3. Réduis les apports d'azote — l'excès aggrave la maladie.\n4. Arrose uniquement le matin, jamais le soir.\nAction immédiate : Traite au Tricyclazole aujourd'hui sans délai."
    },

    # Fusariose maïs
    {
        "instruction": "[Zone: Kolda | Langue: Français]\nMes épis de maïs ont une moisissure rose sur les grains et sentent mauvais.",
        "response": "DANGER : C'est la Fusariose de l'épi (Fusarium verticillioides).\nCes grains contiennent des mycotoxines dangereuses pour la santé.\n1. Ne consomme PAS ces grains avec moisissure rose — ils sont toxiques.\n2. Récolte le reste immédiatement et sèche les grains sains rapidement.\n3. Garde l'humidité des grains stockés en dessous de 14%.\n4. La prochaine saison, contrôle les foreurs de tiges qui favorisent cette maladie.\nAction immédiate : Trie et jette les grains moisissure rose — sèche les autres immédiatement."
    },
]

# ---------------------------------------------------------------------------
# Exemples Wolof — Diagnostics
# ---------------------------------------------------------------------------
EXEMPLES_MALADIES_WO = [
    {
        "instruction": "[Zone: Kaolack | Langue: Wolof]\nFeuilles yu mil dafa set ci jaambur ak poudre bu ñuul ci suuf.",
        "response": "Dafa am Mildiou yu mil (Sclerospora graminicola).\nJamono bu set ak tëmperatuur bu dëkk mooy tax champignon bi.\n1. Tàkk ak jaap léegi feuilles yu set yi ci dëkk bi.\n2. Jëfandikoo Métalaxyl 2g ci 1 litre ndox ci feuilles yu des yi.\n3. Arrosez ci suba rekk, du ngoon ci kanam.\n4. Bàyyil kaw ci kanam ak kanam pour air bi.\nTopp bu nekk ci tékki bi : Jaap feuilles yu set yi lépp tékki bi — du tax leen sëkk ci dëkk bi."
    },
    {
        "instruction": "[Zone: Tambacounda | Langue: Wolof]\nSorgho bi am ndiggël bu mel nit ak odeur bu yaakaar ci panicule bi.",
        "response": "TOPP BI DAFA GAAW : Dafa am Ergot yu sorgho (Claviceps africana).\nGrains yi DAFA DAW — ci nit ak dëkk.\n1. DËGG-DËGG : Jël du grains yi — du lekk ak du jox dëkk.\n2. Tàkk ak jaap panicules yi lépp léegi.\n3. Jëfandikoo Propiconazole 0,5mL/L ci plants yu des yu daan.\n4. Wax agent agricole bi képp.\nTopp bu nekk ci tékki bi : Jaap panicules yi lépp léegi — dafa gaaw."
    },
    {
        "instruction": "[Zone: Ziguinchor | Langue: Wolof]\nFeuilles yu manioc dafa set ak jaambur ci bët — plants yi tuuti.\n",
        "response": "TOPP BI DAFA GAAW : Dafa am Mosaïque yu manioc (African Cassava Mosaic Virus).\nVirus bi dafa yëgël ak yégël ak mouches blanches yi.\n1. Tàkk ak jaap LÉEGI plants yu daan yi — virus bi dafa gaaw.\n2. Jëfandikoo Imidaclopride 0,5mL/L ci plants yu des yi contre mouches blanches.\n3. Jëfandikoo SEULEMENT boutures certifiées pour replanter — du boutures yu daan.\n4. Gis plants yu des yi bépp bés ci ayi ayu.\nTopp bu nekk ci tékki bi : Jaap plants yu daan yi léegi — du tax virus bi yëgël."
    },
    {
        "instruction": "[Zone: Kaffrine | Langue: Wolof]\nAm garab yu ñuul ak yu xonq ci kanam mil bi ak plants yi tuuti lool.",
        "response": "Dafa am Striga — garab bu jël mbëg.\nTànk yi dafa jël ndox ak mbëg ci tànk yu mil bi.\n1. Tàkk Striga AVAN mungi génn fleurs — 1 plant = 50 000 graines.\n2. Du tax Striga am graines ci sa champ — dafa gën ak gën.\n3. Semm niébé wala arachide l'année prochaine — dañu tuer Striga bi.\n4. Jëfandikoo urée micro-dose 2g par poquet pour renforcer mil bi.\nTopp bu nekk ci tékki bi : Tàkk Striga yi lépp avan mungi génn fleurs."
    },
    {
        "instruction": "[Zone: Kaolack | Langue: Wolof]\nGerte yi am taches yu ñuul cerclées de jaune ci feuilles yëpp.",
        "response": "Dafa am Cercosporiose yu gerte (Cercospora arachidicola).\nChampignon bi dafa am lool ci Bassin arachidier bi.\n1. Jëfandikoo Chlorothalonil 2,5g/L léegi.\n2. Répéter ci 2 semaines jusqu'à 6 semaines avan récolte.\n3. Ramasse feuilles yu tooy yi, jaap leen.\n4. Bàyyil kaw pour air bi ci kanam rangs yi.\nTopp bu nekk ci tékki bi : Jëfandikoo Chlorothalonil tékki bi."
    },
    {
        "instruction": "[Zone: Louga | Langue: Wolof]\nÉpis yu mil am nit yu ñuul yu dafa bind ci kanam.",
        "response": "Dafa am Charbon yu mil (Tolyposporium penicillariae).\nChampignon bi soppi grains yi ci spores yu ñuul.\n1. Jaap léegi épis yi — du tax leen sëkk.\n2. DËGG-DËGG : Jël du grains yu ñuul pour semences bi — dañu contaminer lépp.\n3. Tëj semences yi ak Thirame 3g/kg pour l'année prochaine.\n4. Soppi parcelle — jëfandikoo rotation.\nTopp bu nekk ci tékki bi : Tàkk ak jaap épis yu ñuul yi lépp tékki bi."
    },
    {
        "instruction": "[Zone: Kolda | Langue: Wolof]\nDëkk du am azote — plants yi lépp pale ak jaambur, dañu dimbali.",
        "response": "Dafa am carence en azote.\nDëkk bi du am azote — souvent ci ginnaaw ndaw yu dëgël yi.\n1. Jëfandikoo urée (46-0-0) 50kg/hectare ci kanam plants yi.\n2. Wala compost bu dëkk 3 à 5 tonnes/hectare.\n3. Arrose après pour dissoudre engrais bi.\n4. Gis plants yi reverdir ci 5-7 fan.\nTopp bu nekk ci tékki bi : Jëfandikoo urée wala compost tékki bi."
    },
]

# ---------------------------------------------------------------------------
# Exemples météo — Français
# ---------------------------------------------------------------------------
EXEMPLES_METEO_FR = [
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nQuelle est la météo cette semaine à Kaolack ? Dois-je arroser mes cultures ?",
        "response": "Je consulte la météo de Kaolack pour toi.\nSi des pluies sont prévues cette semaine, tu n'as pas besoin d'arroser — laisse la pluie faire le travail et économise ton eau.\nSi l'humidité dépasse 80%, surveille tes cultures pour le mildiou et les champignons — conditions favorables aux maladies fongiques.\nSi la température dépasse 38°C, arrose tôt le matin avant 7h pour limiter l'évaporation.\nAction immédiate : Arrose uniquement le matin et surveille l'humidité."
    },
    {
        "instruction": "[Zone: Thiès | Langue: Français]\nIl va pleuvoir cette semaine à Thiès. Est-ce bon pour mon arachide ?",
        "response": "La pluie modérée est excellente pour l'arachide à Thiès.\nSi plus de 20mm sont prévus, attention au lessivage des engrais que tu viens d'appliquer.\nL'humidité élevée favorise aussi la Cercosporiose — surveille tes feuilles pour des taches brunes.\nNe traite pas avec des fongicides juste avant la pluie — ça sera lavé immédiatement.\nAction immédiate : Surveille les feuilles après la pluie pour détecter les premières taches."
    },
    {
        "instruction": "[Zone: Saint-Louis | Langue: Français]\nLa météo à Saint-Louis cette semaine pour mon riz ?",
        "response": "Saint-Louis bénéficie généralement d'une météo favorable pour le riz irrigué.\nSi l'humidité est élevée cette semaine, surveille les taches en losange sur tes feuilles — c'est le blast du riz.\nUn vent fort peut favoriser la verse — attache tes plants si nécessaire.\nÉvite d'arroser le soir par temps humide.\nAction immédiate : Vérifie tes feuilles de riz pour des taches en losange si l'humidité est forte."
    },
    {
        "instruction": "[Zone: Ziguinchor | Langue: Français]\nBeaucoup de pluie prévue en Casamance. Qu'est-ce que je dois faire pour mon manioc ?",
        "response": "La Casamance avec ses pluies abondantes est idéale pour le manioc.\nMais beaucoup de pluie augmente le risque de mouches blanches — vecteurs de la Mosaïque.\nSurveille les nouvelles feuilles : si elles sont tachetées jaune-vert, c'est la mosaïque.\nAssure un bon drainage autour de tes plants pour éviter la pourriture des racines.\nAction immédiate : Inspecte les nouvelles pousses après la pluie pour détecter la mosaïque."
    },
    {
        "instruction": "[Zone: Tambacounda | Langue: Français]\nGrande chaleur prévue cette semaine à Tambacounda. Comment protéger mon sorgho ?",
        "response": "La chaleur intense à Tambacounda peut stresser ton sorgho.\nArrose tôt le matin avant 7h pour éviter l'évaporation — jamais en pleine journée.\nLa chaleur + sécheresse favorise le développement de l'ergot si ta culture est à la floraison.\nSurveille les panicules pour tout liquide collant sucré — c'est le premier signe de l'ergot.\nAction immédiate : Arrose tôt le matin et vérifie tes panicules chaque jour cette semaine."
    },
]

# ---------------------------------------------------------------------------
# Exemples météo — Wolof
# ---------------------------------------------------------------------------
EXEMPLES_METEO_WO = [
    {
        "instruction": "[Zone: Kaolack | Langue: Wolof]\nNdaw bi dafa nekk fan yi ak Kaolack ? Dafa wàcc ndox ci sa cultures ?",
        "response": "Jëfandikoo météo bi ci Kaolack pour sa réponse.\nBu ndaw am ci ayu fan yi, arrose du — bàyyil ndaw bi def ko.\nBu humidité bi gën 80%, gis cultures yi pour mildiou — conditions bu rafet pour champignons.\nBu tëmperatuur bi gën 38°C, arrose ci suba rekk avan 7h du matin.\nTopp bu nekk ci tékki bi : Arrose ci suba rekk ak gis humidité bi."
    },
    {
        "instruction": "[Zone: Thiès | Langue: Wolof]\nNdaw bi dafa doon ci Thiès. Dafa rafet ci gerte yi ?",
        "response": "Ndaw bu tuuti dafa rafet lool ci gerte yi ci Thiès.\nBu gën 20mm, gis lessivage yu engrais yu nga jëfandikoo.\nHumidité bi dafa tax Cercosporiose — gis feuilles yi pour taches yu ñuul.\nDu traiter ci kanam ndaw bi — dina lekk.\nTopp bu nekk ci tékki bi : Gis feuilles yi ci ginnaaw ndaw bi pour taches."
    },
]

# ---------------------------------------------------------------------------
# Exemples prix marché — Français
# ---------------------------------------------------------------------------
EXEMPLES_PRIX_FR = [
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nQuel est le prix de l'arachide au marché cette saison ?",
        "response": "Le prix de l'arachide est actuellement autour de 350 FCFA par kg au Sénégal.\nLa tendance est à la hausse cette saison.\nLe meilleur marché pour vendre ton arachide est Kaolack ou Ziguinchor.\nConseil : ne vends pas tout immédiatement après la récolte — attends quelques semaines car les prix montent généralement après la récolte massive.\nAction immédiate : Renseigne-toi sur le prix exact au marché local avant de vendre."
    },
    {
        "instruction": "[Zone: Thiès | Langue: Français]\nCombien coûte le mil au marché de Thiès ?",
        "response": "Le prix du mil est actuellement autour de 175 FCFA par kg.\nLa tendance est stable cette saison.\nLes meilleurs marchés pour le mil sont Thiès et Diourbel.\nC'est une période correcte pour vendre si tu as besoin d'argent rapidement.\nAction immédiate : Vérifie le prix exact au marché de Thiès avant de décider."
    },
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nJe veux vendre mon niébé. Quel est le meilleur prix ?",
        "response": "Le prix du niébé est actuellement autour de 450 FCFA par kg — c'est une des cultures les mieux valorisées.\nLa tendance est stable cette saison.\nLes meilleurs marchés sont Kolda et Kaffrine.\nLe niébé se conserve bien — tu peux attendre 2 à 3 mois après la récolte pour vendre si les prix remontent.\nAction immédiate : Compare les prix au marché local avec les marchés de Kolda avant de vendre."
    },
    {
        "instruction": "[Zone: Kolda | Langue: Français]\nPrix du manioc et où vendre ?",
        "response": "Le prix du manioc est actuellement autour de 80 FCFA par kg.\nLes meilleurs marchés pour vendre ton manioc sont Ziguinchor et Kolda — qui est près de toi.\nLe manioc étant périssable, vends rapidement après récolte pour éviter les pertes.\nConsidère la transformation en attiéké ou en farine de manioc pour augmenter la valeur.\nAction immédiate : Contacte les commerçants de Kolda pour connaître leur prix d'achat."
    },
    {
        "instruction": "[Zone: Saint-Louis | Langue: Français]\nQuel est le prix du riz local au marché ?",
        "response": "Le prix du riz local est autour de 400 FCFA par kg — bien valorisé par rapport au riz importé.\nLa tendance est stable.\nLes meilleurs marchés sont en Casamance et dans le Delta du Fleuve Sénégal.\nLe riz local est de plus en plus demandé par les consommateurs — c'est une bonne période pour vendre.\nAction immédiate : Renseigne-toi auprès des transformateurs locaux pour les prix d'achat en gros."
    },
    {
        "instruction": "[Zone: Louga | Langue: Français]\nPrix de l'oignon cette saison ?",
        "response": "Le prix de l'oignon est actuellement autour de 250 FCFA par kg avec une tendance à la hausse.\nLes meilleurs marchés sont Saint-Louis et Louga — qui est ta zone.\nL'oignon sénégalais est très demandé — surtout après la contre-saison de Saint-Louis.\nConserve bien ton oignon dans un endroit sec et aéré pour profiter de la hausse des prix.\nAction immédiate : Contacte les grossistes de Louga pour négocier le meilleur prix."
    },
]

# ---------------------------------------------------------------------------
# Exemples prix marché — Wolof
# ---------------------------------------------------------------------------
EXEMPLES_PRIX_WO = [
    {
        "instruction": "[Zone: Kaolack | Langue: Wolof]\nNaka xaalis bi ci gerte ci marché bi ?",
        "response": "Prix yu gerte dafa nekk ci 350 FCFA/kg léegi ci Sénégal bi.\nTendance bi dafa yëgël — rafet pour jaay.\nMarché bu bax pour jaay sa gerte mooy Kaolack wala Ziguinchor.\nDu jaay lépp ci kanam récolte bi — attends quelques semaines, prix bi dina yëgël.\nTopp bu nekk ci tékki bi : Jël xam-xam prix bi exact ci marché local avan nga jaay."
    },
    {
        "instruction": "[Zone: Kolda | Langue: Wolof]\nNaka xaalis bi ci nebe ci marché bi ?",
        "response": "Prix yu nebe dafa nekk ci 450 FCFA/kg — culture bu bax lool.\nTendance bi dafa stable ci saison bi.\nMarché bu bax mooy Kolda ak Kaffrine.\nNebe bi dafa soxor — mën nga attends 2-3 mois avan nga jaay bu prix bi yëgël.\nTopp bu nekk ci tékki bi : Tëkkël prix bi ci marché local ak Kolda avan nga décider."
    },
]

# ---------------------------------------------------------------------------
# Exemples questions générales agriculture
# ---------------------------------------------------------------------------
EXEMPLES_GENERAUX_FR = [
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nQuand est-ce que je dois semer mon mil pour avoir une bonne récolte ?",
        "response": "Au Sénégal, le mil se sème en début de saison des pluies — généralement entre mi-juin et fin juillet selon ta zone.\nÀ Kaolack, vise le mois de juillet quand les pluies sont bien installées.\nSème dès que tu as eu 2 à 3 pluies consécutives d'au moins 20mm.\nAttends trop tard et tu risques que le mil manque de pluie à la floraison.\nAction immédiate : Prépare tes semences maintenant et surveille les premières pluies."
    },
    {
        "instruction": "[Zone: Thiès | Langue: Français]\nComment faire un bon compost pour mes cultures ?",
        "response": "Un bon compost se fait en 2 à 3 mois avec des matières simples.\n1. Mélange déchets végétaux, paille, fumier animal et un peu de terre.\n2. Humidifie régulièrement mais sans noyer — le tas doit rester humide comme une éponge.\n3. Retourne le tas toutes les 2 semaines pour aérer et accélérer la décomposition.\n4. Le compost est prêt quand il est brun, sans odeur forte et friable.\nAction immédiate : Commence ton tas de compost maintenant pour être prêt pour la prochaine saison."
    },
    {
        "instruction": "[Zone: Kolda | Langue: Français]\nQuelle rotation pratiquer avec l'arachide pour améliorer mon sol ?",
        "response": "La meilleure rotation avec l'arachide est : arachide → mil ou sorgho → légumineuse.\nL'arachide fixe l'azote dans le sol — le mil qui suit en profite.\nÉvite de faire arachide après arachide — ça favorise la Cercosporiose et épuise le sol.\nSème du niébé une année sur trois — il fixe encore plus d'azote et diversifie tes revenus.\nAction immédiate : Planifie tes parcelles maintenant pour la prochaine saison."
    },
    {
        "instruction": "[Zone: Saint-Louis | Langue: Français]\nComment stocker correctement mon mil après la récolte ?",
        "response": "Un bon stockage du mil peut le conserver 1 à 2 ans sans perte importante.\n1. Sèche bien le mil avant stockage — humidité inférieure à 13%.\n2. Stocke dans des sacs propres, secs, surélevés du sol sur des palettes.\n3. Protège contre les insectes avec des feuilles de neem ou de la cendre de bois.\n4. Inspecte ton stock tous les 2 mois et retourne les sacs.\nAction immédiate : Vérifie l'humidité de ton mil avant de le stocker."
    },
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nMes plants de mil sont attaqués par des chenilles qui mangent les feuilles.",
        "response": "Ce sont probablement des chenilles de la légionnaire d'automne (Spodoptera frugiperda) ou des chenilles de la pyrale.\n1. Traite avec un insecticide autorisé à base de Lambda-cyhalothrine 15mL/L dès que tu vois les dégâts.\n2. Traite le soir quand les chenilles sont actives.\n3. Pour une approche naturelle, utilise une solution de cendre de bois diluée dans l'eau.\n4. Surveille chaque matin les nouvelles feuilles et les points de croissance.\nAction immédiate : Inspecte le soir et traite si tu trouves des chenilles actives."
    },
    {
        "instruction": "[Zone: Ziguinchor | Langue: Français]\nMes tomates ne produisent pas de fruits, les fleurs tombent.",
        "response": "La chute des fleurs de tomate a plusieurs causes possibles à Ziguinchor.\nSi la chaleur dépasse 35°C, le pollen devient stérile — c'est la cause la plus fréquente.\nSi l'arrosage est irrégulier, ça stress la plante et fait tomber les fleurs.\nSi tu as beaucoup de pucerons ou de thrips, ils peuvent transmettre des virus.\nVérifie aussi si les feuilles s'enroulent vers le haut — ce serait le TYLCV.\nAction immédiate : Régularise l'arrosage et vérifie l'état des feuilles pour des insectes."
    },
    {
        "instruction": "[Zone: Kaolack | Langue: Français]\nComment préparer mon sol avant le semis du mil ?",
        "response": "Une bonne préparation du sol est essentielle pour un bon rendement du mil.\n1. Laboure à 20-25cm de profondeur après les premières pluies.\n2. Apporte du compost ou du fumier décomposé : 2 à 3 tonnes par hectare.\n3. Nivelez le sol pour éviter les zones d'accumulation d'eau.\n4. Si tu peux, fais un faux-semis — tu laboures, tu attends 2 semaines que les adventices germent, puis tu herbes avant de semer.\nAction immédiate : Commence le labour dès les premières pluies significatives."
    },
]

# ---------------------------------------------------------------------------
# Exemples généraux en Wolof
# ---------------------------------------------------------------------------
EXEMPLES_GENERAUX_WO = [
    {
        "instruction": "[Zone: Kaolack | Langue: Wolof]\nFan mooy rafet pour semm mil ci Kaolack ?",
        "response": "Ci Sénégal, semm mil dafa nekk ci kanam saison yu ndaw — généralement entre mi-juin et fin juillet.\nCi Kaolack, vise juillet bu ndaw yi dëkk.\nSemm bu nga am 2-3 pluies yi ci 20mm.\nBu tarder lool, mil bi dina manqu ndaw ci floraison bi.\nTopp bu nekk ci tékki bi : Prépare semences yi légi ak gis pluies yu njëkk yi."
    },
    {
        "instruction": "[Zone: Kaolack | Langue: Wolof]\nLoo def pour soxor correctement mil bi ci ginnaaw récolte bi ?",
        "response": "Stockage bu rafet mën tax mil bi soxor 1 à 2 ans sans problème.\n1. Sëkk mil bi avan stockage — humidité inférieure à 13%.\n2. Soxor ci sacs yu set, yu sëkk, surélevés du sol.\n3. Protège contre insectes ak feuilles neem wala cendre bois.\n4. Gis stock bi ci 2 mois ak retourne sacs yi.\nTopp bu nekk ci tékki bi : Vérifie humidité yu mil bi avan stockage."
    },
    {
        "instruction": "[Zone: Thiès | Langue: Wolof]\nNaka def compost bu rafet ci cultures yi ?",
        "response": "Compost bu rafet dafa def ci 2 à 3 mois ak matières yu yomb.\n1. Mélanges déchets végétaux, paille, fumier ak tëgg.\n2. Humidifie régulièrement — mélanges dafa nekk mel ni éponge bu nit.\n3. Retourne ci 2 semaines pour aérer.\n4. Compost bi ready bu dafa ñuul, sans odeur forte ak friable.\nTopp bu nekk ci tékki bi : Commencer tas compost légi pour l'année prochaine."
    },
]

# ---------------------------------------------------------------------------
# Assembler tout le dataset
# ---------------------------------------------------------------------------
def build_dataset():
    all_examples = (
        EXEMPLES_MALADIES_FR +
        EXEMPLES_MALADIES_WO +
        EXEMPLES_METEO_FR +
        EXEMPLES_METEO_WO +
        EXEMPLES_PRIX_FR +
        EXEMPLES_PRIX_WO +
        EXEMPLES_GENERAUX_FR +
        EXEMPLES_GENERAUX_WO
    )

    # Formater en chat template Gemma 4
    formatted = []
    for ex in all_examples:
        formatted.append({
            "conversations": [
                {
                    "role": "system",
                    "content": (
                        "Tu es FarmSense, un assistant agricole pour les petits agriculteurs "
                        "du Sénégal et du Sahel. Tu parles Français et Wolof. "
                        "Tu es direct et pratique. "
                        "RÈGLES : Jamais de markdown. Texte simple. Maximum 8 lignes. "
                        "Structure : diagnostic / cause / actions numérotées / action immédiate. "
                        "Réponds dans la langue du contexte (Français ou Wolof)."
                    )
                },
                {
                    "role": "user",
                    "content": ex["instruction"]
                },
                {
                    "role": "assistant",
                    "content": ex["response"]
                }
            ]
        })

    # Mélanger les exemples
    random.shuffle(formatted)

    return formatted


if __name__ == "__main__":
    dataset = build_dataset()

    # Sauvegarder en JSONL
    output_path = "farmsense_dataset.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for example in dataset:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")

    print(f"Dataset généré : {len(dataset)} exemples")
    print(f"Fichier : {output_path}")
    print(f"\nRépartition :")
    print(f"  Maladies FR  : {len(EXEMPLES_MALADIES_FR)}")
    print(f"  Maladies WO  : {len(EXEMPLES_MALADIES_WO)}")
    print(f"  Météo FR     : {len(EXEMPLES_METEO_FR)}")
    print(f"  Météo WO     : {len(EXEMPLES_METEO_WO)}")
    print(f"  Prix FR      : {len(EXEMPLES_PRIX_FR)}")
    print(f"  Prix WO      : {len(EXEMPLES_PRIX_WO)}")
    print(f"  Généraux FR  : {len(EXEMPLES_GENERAUX_FR)}")
    print(f"  Généraux WO  : {len(EXEMPLES_GENERAUX_WO)}")
