<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-VOICE-UI banner" width="100%">
</p>

# 🎙️ HYDRA-UMC-VOICE-UI

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | 🇫🇷 <b>Français</b> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🔊 Pipeline Speech-to-Action locale accélérée par le matériel

<p align="left">
  <img src="https://img.shields.io/badge/Licence-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/STT-Whisper%20Local-FF6F00.svg" alt="STT">
  <img src="https://img.shields.io/badge/Plateforme-Hailo--10-green.svg" alt="Hailo-10">
</p>

---

## 1. 🛠️ APERÇU TECHNIQUE

**HYDRA-UMC-VOICE-UI** est la couche d'interaction vocale locale pour l'écosystème HYDRA-UMC. Il fournit un pipeline STT (Speech-to-Text) et TTS (Text-to-Speech) haute performance accéléré par le NPU Hailo-10.

Il permet aux opérateurs de contrôler les missions robotiques, de consulter l'état du système et de recevoir un retour audio sans aucune connectivité cloud, garantissant une confidentialité maximale et une latence nulle.

### Caractéristiques principales :
* 🎧 **Front-end audio (v0) :** Chargement WAV réel, stdlib pur, et détection d'activité vocale par seuil d'énergie. *(implémenté comme une vraie primitive de traitement du signal - pas la transcription elle-même ; voir BUILD ET EXÉCUTION ci-dessous)*
* 🎙️ **Edge STT :** Modèles Whisper quantifiés pour une transcription vocale quasi instantanée. *(prévu - nécessite une vraie dépendance de modèle)*
* 📢 **TTS naturel :** Synthèse vocale de haute qualité pour les alertes système et les rapports d'état. *(prévu)*
* 🧠 **Analyseur NLU (v0) :** Extraction réelle d'intention/entités du texte reconnu, à base de règles, pour le planificateur sémantique. *(implémenté comme des règles regex sur un petit vocabulaire réel de commandes - pas un modèle de ML entraîné ; voir BUILD ET EXÉCUTION ci-dessous)*
* 🔀 **Classification consciente de l'ambiguïté :** `classify_intent()` normalise le texte (Unicode NFKC, suppression des mots de remplissage/ponctuation) et rejette une transcription qui correspond réellement à plus d'une commande connue au lieu de deviner silencieusement laquelle. *(implémenté ; utilisé par la passerelle vocale Watch ci-dessous)*
* 🛡️ **Suppression du bruit :** Optimisé pour les environnements industriels avec un bruit ambiant élevé. *(prévu)*
* 👨‍👩‍👧 **Enfant du Cognitive AI Node :** Fonctionne comme l'un des
  quatre services frères sous [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)
  (aux côtés de VLA-Engine, Semantic-Planner et Docs-QA), partageant
  l'image HydraOS et les poids de modèles de son parent au lieu de
  conserver ses propres copies.
* 📦 **Versionnage compteur kilométrique :** Chaque build réel incrémente
  automatiquement la version de `pyproject.toml` (`bump_version.py`) - pas
  de modification manuelle de version.

---

## 2. 🔄 FLUX DU PIPELINE VOCAL

```mermaid
flowchart LR
    MIC["Entrée microphone"] --> STT["Whisper STT (Hailo-10)"]
    STT --> NLU["Analyseur d'intention sémantique"]
    NLU --> LOGIC["Logique du nœud cognitif"]
    LOGIC --> TTS["Moteur TTS"]
    TTS --> SPK["Sortie haut-parleur"]
```

---

## 3. 🧱 ARCHITECTURE & DÉCISIONS DE CONCEPTION

Ce dépôt est un **enfant** de la famille Cognitive AI Node - son parent,
[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE),
détient l'image HydraOS partagée et les poids de modèles quantifiés, et
relie ce service dans son `docker-compose.yml` aux côtés de ses trois
frères (VLA-Engine, Semantic-Planner, Docs-QA) :

* **Pourquoi cet enfant n'a pas de matériel/firmware/`os/`/`models/`
  propres.** Il fonctionne entièrement sur le module CM5 + Hailo-10 M.2
  déjà détenu par le parent - centraliser les poids de modèles et
  l'image HydraOS à un seul endroit évite quatre copies divergentes de
  plusieurs gigaoctets au sein de la famille.
* **Pourquoi une structure `src/`.** Sépare le paquet installable
  (`hydra_umc_voice_ui`) de l'outillage à la racine du dépôt
  (`bump_version.py`), conformément au reste des projets Python de
  l'écosystème.
* **Pourquoi le point d'entrée se contente d'afficher
  identité/version/rôle aujourd'hui.** C'est l'étape d'échafaudage :
  prouver que le paquet s'installe, se compile et s'importe correctement
  - sur la version Python cible réelle - est un prérequis avant d'ajouter
  une vraie logique de pipeline STT/TTS, et isole ce travail ultérieur
  des préoccupations d'empaquetage.
* **Comment cela s'intègre dans le reste de l'écosystème.** Ce service
  est le point d'entrée mains libres de tout le Cognitive AI Node :
  l'intention reconnue circule vers son frère
  HYDRA-UMC-SEMANTIC-PLANNER, et il agit comme surface de contrôle vocal
  aux côtés de HYDRA-UMC-STUDIO et HYDRA-UMC-DSI.
* **Pourquoi `audio.py` utilise `wave`/`array` plutôt que numpy.** Le
  décodage PCM 16 bits et une vraie VAD par seuil d'énergie ne
  nécessitent rien au-delà de ce que la stdlib fournit déjà - garder v0
  sans dépendance signifie que le vrai front-end audio fonctionne
  partout où Python s'exécute, avant même qu'une dépendance STT
  spécifique au Hailo-10 soit installée.
* **Pourquoi `intent.py` est de vraies règles regex, pas un modèle NLU
  entraîné.** Un petit vocabulaire réel de commandes
  (start/stop/status/go home) est entièrement et honnêtement couvert
  par des règles aujourd'hui - le même raisonnement que le vrai index
  TF-IDF du frère HYDRA-UMC-DOCS-QA plutôt qu'un modèle d'embeddings :
  un noyau réel et testable maintenant, qu'un futur classificateur basé
  sur le ML pourra remplacer derrière le même contrat
  `parse_intent()`, une fois que la parole reconnue devra couvrir plus
  que ce vocabulaire v0.
* **Pourquoi un audio/texte sans correspondance renvoie un échec
  honnête, pas une supposition.** `detect_voice_segments()` renvoie une
  liste vide pour le silence, et `parse_intent()` renvoie `None` pour un
  texte hors de son jeu de règles - v0 n'a pas de modèle de repli, donc
  il n'invente jamais un segment ou une intention qu'il n'a pas
  réellement détecté.
* **Pourquoi la passerelle Watch utilise `classify_intent()`, et non
  l'ancien `parse_intent()`.** `parse_intent()` reste "la première
  correspondance gagne" (inchangé, toujours testé tel quel) pour les
  appelants existants, mais une transcription réelle qui correspond
  réellement à plus d'une commande connue (par exemple contenant à la
  fois "stop" et "status") est une ambiguïté réelle et pertinente pour
  la sécurité dans une passerelle dont tout le rôle est de décider si
  une commande de mouvement nécessite une confirmation -
  `classify_intent()` vérifie chaque règle et signale un cas
  d'ambiguïté réel et distinct au lieu de le résoudre silencieusement
  vers la règle déclarée en premier.
* **Pourquoi `normalize_text()` applique Unicode NFKC avant la mise en
  correspondance.** Certains pipelines speech-to-text émettent des
  lettres latines pleine chasse et d'autres formes Unicode de
  compatibilité - des points de code distincts des caractères ASCII
  ordinaires, et donc pas "le mot" du point de vue d'une expression
  régulière `\b...\b`. NFKC les ramène d'abord à leur équivalent
  ordinaire, afin qu'une commande sémantiquement identique à une règle
  connue ne soit jamais traitée comme un échec honnête simplement à
  cause de son encodage.

---

## 📂 STRUCTURE DES RÉPERTOIRES

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/
│   ├── audio.py               # Chargement WAV réel + détection d'activité vocale par énergie
│   ├── intent.py               # Analyseur réel d'intention/entités à base de règles + classify_intent() conscient de l'ambiguïté
│   ├── gateway.py               # Passerelle texte-vers-intention bornée, partagée par le flux cognitif Watch
│   ├── http_service.py          # Petite frontière HTTP stdlib pour le chemin vocal Watch-vers-cognitif
│   └── main.py                  # Point d'entrée + sous-commandes réelles `analyze-audio`/`parse-intent`
├── tests/                    # Tests réels : fixtures WAV, VAD, règles d'intention, gateway, CLI de bout en bout
├── docs/                     # Documentation et catalogue de commandes
├── images/                   # Médias et diagrammes
├── deploy/
│   └── voice-ui.env.example  # Modèle d'environnement de la passerelle locale sur la CM5
├── systemd/
│   └── hydra-umc-voice-ui.service # Unité systemd du service HTTP vocal local sur la CM5
├── tools/
│   ├── build_test.py         # Vérification de build sans versionnage
│   └── ci_validate.py        # Validation manifeste/CHANGELOG/docs utilisée par CI
├── build/                    # Sortie de build locale (ignorée par git)
├── pyproject.toml            # Métadonnées du paquet (version à incrément type compteur kilométrique)
├── bump_version.py           # Incrément de version native type compteur kilométrique (utilisé par build.sh/.bat)
├── bump_manifest_version.py  # Synchronise la version de hydra-umc.project.json avec la version native (--sync)
├── build.sh / build.bat      # Crée le venv, installe (avec extras dev), vérifie l'import, exécute les tests
└── run.sh / run.bat          # Exécute le point d'entrée (transmet les arguments, ex. `analyze-audio`)
```

> **Remarque :** `hardware/` et `firmware/` ont été supprimés - ce nœud
> fonctionne sur un module CM5 + Hailo-10 M.2 déjà existant, sans
> conception matérielle/firmware propre. `os/` et `models/` ont également
> été supprimés - l'image HydraOS et les poids de modèles Hailo-10
> partagés se trouvent dans le projet parent
> `HYDRA-UMC-COGNITIVE-NODE`, auquel ce projet se rattache en tant que
> service (voir son `docker-compose.yml`).

---

## ⚙️ BUILD ET EXÉCUTION

Nécessite Python >= 3.10.

```bash
# Linux / macOS / Git Bash
./build.sh   # crée .venv, installe le paquet (éditable), vérifie l'import
./run.sh     # exécute le point d'entrée

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` incrémentent la version (type compteur
kilométrique, voir `bump_version.py`) avant chaque build réel, et
exécutent la vraie suite de tests (`pytest tests/`). Sortie attendue
d'un `run.sh` sans argument :

```text
HYDRA-UMC-VOICE-UI v0.1.0
Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free robotic mission control.
```

Les vraies sous-commandes analysent un fichier WAV ou traitent du texte
déjà transcrit :

```bash
./run.sh analyze-audio recordings/command.wav
./run.sh parse-intent "start mission alpha"

# Windows
run.bat analyze-audio recordings\command.wav
run.bat parse-intent "status of robot 3"
```

### 🩺 Dépannage

* **`python : commande introuvable` / le build échoue à l'étape 1.**
  Nécessite Python >= 3.10 dans le `PATH`. Sous Windows, installez-le
  depuis [python.org](https://python.org) et cochez "Add to PATH" lors de
  l'installation ; sous Linux/macOS, c'est généralement `python3`.
* **`build.sh` n'arrive pas à activer le venv.** `python3 -m venv .venv`
  place le script d'activation à un emplacement différent selon la
  plateforme : `.venv/bin/activate` sous Linux/macOS,
  `.venv/Scripts/activate` sous Windows (également pour un venv Python
  Windows utilisé depuis Git Bash). `build.sh` vérifie déjà les deux
  chemins - si cela échoue toujours, supprimez `.venv/` et relancez
  `./build.sh` pour le reconstruire entièrement.
* **`pip install -e .` échoue.** Généralement dû à un `.venv/` obsolète.
  Supprimez le dossier `.venv/` et relancez `./build.sh`/`build.bat` pour
  le recréer.
* **`import OK` ne s'affiche jamais.** Signifie que `python -c "import
  hydra_umc_voice_ui"` a lui-même échoué - relancez avec le venv actif
  pour voir la vraie trace d'erreur.

---

## 🎙️ PASSERELLE VOCALE POUR WATCH (v0)

`python -m hydra_umc_voice_ui.main serve` expose une passerelle HTTP locale volontairement limitée pour une intégration appairée avec HYDRA-UMC-WATCH : `GET /health` et `POST /v1/voice/turn`. Elle valide le message typé `voice_turn`, utilise l'analyseur d'intentions déterministe existant et renvoie `assistant_reply` ; elle ne contrôle aucun matériel robotique.

Le développement en loopback peut fonctionner sans jeton. Une écoute hors loopback exige `HYDRA_UMC_VOICE_UI_TOKEN` et un en-tête `Authorization: Bearer` correspondant. Cette API ne transporte jamais d'audio brut et les intentions liées au mouvement renvoient toujours `requiresConfirmation: true`.

Une transcription qui correspond réellement à plus d'une commande connue est rejetée avec une réponse réelle et distincte au lieu d'être résolue silencieusement vers une seule interprétation :

```json
{"transcript": "stop the status check"}
// -> {"text": "That request matched more than one action (status, stop). Please rephrase it more specifically.", "requiresConfirmation": false, "intent": null}
```

Consultez [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) pour le contrat de requête et la limite de déploiement.

## 🚀 FEUILLE DE ROUTE
* **Phase 1 :** Déploiement du moteur VLA et traitement des entrées multimodales sur Hailo-10.
* **Phase 2 :** Intégration du planificateur sémantique avec des modèles de comportement en essaim et une mémoire à long terme.
* **Phase 3 :** Exécution locale à faible latence de l'interface vocale et suppression du bruit industriel.
* **Phase 4 :** Prise en charge multilingue (anglais, espagnol, allemand, français) et intégration complète avec Dashboard AI.

---

## 🔗 Projets Liés

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Projet Parent**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub d'intégration pour le pipeline cognitif Hailo-10 (orchestration LLM/VLA/voix) ; le parent dont ce dépôt est une étape ou un consommateur spécifique, au sein de son propre pipeline cognitif.

**Projets Frères** — les autres étapes/consommateurs du propre pipeline cognitif Hailo-10 de HYDRA-UMC-COGNITIVE-NODE
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vraie décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vrai encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vraie recherche documentaire TF-IDF (bibliothèque standard uniquement) sur les propres documents Markdown de cet écosystème.

**Directement Liés**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel ; une autre surface de contrôle vocal de l'écosystème, aux côtés de ce service.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran tactile DSI 7" embarqué, intégrée directement sur le CM5 ; une autre surface de contrôle vocal de l'écosystème, aux côtés de ce service.

**Fait Également Partie de l'Écosystème**

*Matériel & Plateforme de Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère physique du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, coordonnant jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible sur Raspberry Pi OS pour le CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi de premier contact.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé et la barrière de sécurité contre laquelle chaque bridge valide ses commandes.

*Backend Central & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande d'essaim de bureau (PySide6) pour plusieurs serveurs à la fois, empaqueté en exécutable autonome.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et un compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui envoie les modèles terminés vers le propre catalogue de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour les flottes AGV/AMR via un éditeur MQTT VDA 5050 réel.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur haut niveau pour cellules CNC avec accès réel au statut/octets de contrôle GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un véritable émetteur de commandes Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de sécurité pour cellules laser lisant 3 vraies sécurités GPIO de clé/enceinte/verrouillage.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur haut niveau sûr pour le flux de cartes du pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec de vraies commandes de tâche contrôlées.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur de sécurité avec un vrai transport ROS 2 rclpy à importation paresseuse.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméra, avec un véritable émetteur de commandes MAVLink.

*Plateforme d'Outils URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, plus de 25 profils d'outil sur bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau à interface graphique pour flasher les cartes URTC, CAN-OTA plus SWD/JTAG puce complète.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic CAN-bus en direct pour cartes URTC, un panneau par profil d'outil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée navigateur à URTC-TESTER via la Web Serial API, sans installation locale.

*Nœud IA de Vision (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline de vision Hailo-8, avec une vraie vérification de disponibilité matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sécurisé par architecture Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + config MediaMTX, avec une vraie frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vraie loi de correction Position-Based Visual Servoing, verrouillée sur l'état de zone en amont.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vraie vérification de violation de zone et demande d'E-STOP, avec application de la fraîcheur de calibration.

*Orchestration & Essaim*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un vrai contrat de rapport de santé gRPC/Protobuf et une machine à états de mission.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vraie file de tâches basée sur la priorité avec déduplication, via une vraie API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vrai chien de garde de santé de flotte basé sur gRPC, avec retry/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vrai planificateur de trajectoire 3D basé sur RRT, avec vraie validation des collisions obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vraie synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un vrai contrat de synchronisation par compatibilité de version.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vrai verrouillage de sécurité hardware-in-the-loop routant les commandes entre simulation et matériel réel.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vraie cinématique directe et validation des limites articulaires sur un vrai sous-ensemble URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vrai générateur procédural de scènes 2D avec export d'annotations YOLO/COCO.

*Données & Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vrai magasin de séries temporelles basé sur sqlite3, avec une vraie API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vrai détecteur d'anomalies FFT + ligne de base statistique, avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vrai calcul OEE/disponibilité sur l'historique de DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vrai pipeline d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication par séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub d'intégration relayant vers les protocoles industriels, avec une vraie couche de liste blanche de commandes/contre-pression.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vrai espace d'adressage OPC-UA, vérifié avec une vraie session client du protocole binaire.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vrai broker MQTT avec authentification par client optionnelle et ACL de sujets.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — vrais points de terminaison XML MTConnect `/probe` et `/current`, avec sortie en mode dégradé.

*Outils Complémentaires & Opérations de l'Écosystème*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux Smart Summaries et Anomaly Highlighting sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un vrai contrat de codes de sortie stable, un vrai client en direct de la propre API de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec de vraies alertes haptiques et un relais vocal vers le téléphone jumelé.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un vrai compagnon de vision Python pour une tête d'outil d'inspection thermique/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — outil administratif de bureau qui découvre, clone et met à jour chaque dépôt de cet écosystème.

---

## 👤 AUTEUR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCE
GPL-3.0 - Voir le fichier LICENSE pour plus de détails.
