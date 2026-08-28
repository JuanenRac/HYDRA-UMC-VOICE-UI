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

---

## 📂 STRUCTURE DES RÉPERTOIRES

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/
│   ├── audio.py               # Chargement WAV réel + détection d'activité vocale par énergie
│   ├── intent.py               # Analyseur réel d'intention/entités à base de règles
│   └── main.py                  # Point d'entrée + sous-commandes réelles `analyze-audio`/`parse-intent`
├── tests/                    # Tests réels : fixtures WAV, VAD, règles d'intention, CLI de bout en bout
├── docs/                     # Documentation et catalogue de commandes
├── images/                   # Médias et diagrammes
├── scripts/                  # Scripts utilitaires
├── build/                    # Sortie de build locale (ignorée par git)
├── pyproject.toml            # Métadonnées du paquet (version 0.0.5, incrément type compteur kilométrique)
├── bump_version.py           # Incrément de version type compteur kilométrique (utilisé par build.sh/.bat)
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
HYDRA-UMC-VOICE-UI v0.0.5
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

Consultez [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) pour le contrat de requête et la limite de déploiement.

## 🚀 ROADMAP
* **Phase 1 :** Déploiement du moteur VLA et traitement des entrées multimodales sur Hailo-10.
* **Phase 2 :** Intégration du planificateur sémantique avec des modèles de comportement en essaim et une mémoire à long terme.
* **Phase 3 :** Exécution locale à faible latence de l'interface vocale et suppression du bruit industriel.
* **Phase 4 :** Prise en charge multilingue (anglais, espagnol, allemand, français) et intégration complète avec Dashboard AI.

---

## 🔗 PROJETS LIÉS

Ce projet fait partie d'un écosystème robotique plus large du même auteur (JuanenRac / Electro Hobby 3D), couvrant firmware, logiciel de contrôle, nœuds IA et outillage de flotte.

### Directement liés à ce service

- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** / **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — autres surfaces de contrôle vocal de l'écosystème.

### Reste de l'écosystème

**Plateforme HYDRA-UMC** — la micro-usine multi-robots
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère elle-même : hôte Raspberry Pi CM5 + coprocesseur temps réel STM32H745 double cœur, orchestrant jusqu'à 8 bras robotiques distribués via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — backend Express/WebSocket headless détenant l'état des robots.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application Android de contrôle pour HYDRA-UMC.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application iOS/iPadOS de contrôle pour HYDRA-UMC.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande de bureau pour l'essaim.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour modèles URDF.

**Plateforme URTC** — le contrôleur de tête d'outil que porte chaque bras HYDRA-UMC
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller, firmware.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau de flashage CAN-OTA + SWD/JTAG.
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic CAN en direct.
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative navigateur aux 2 outils de bureau ci-dessus.

**👁️ Vision AI Node (Hailo-8)**
- [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)
- [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)
- [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)
- [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)
- [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)

**🐝 Orchestration & Swarm**
- [HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)
- [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)
- [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)
- [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)
- [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)

**🎮 Digital Twin & Simulation**
- [HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)
- [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)
- [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)
- [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)

**📊 Data & Analytics**
- [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)
- [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)
- [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)
- [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)

**🏭 Industrial Gateway**
- [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)
- [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)
- [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)
- [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)

**🛠️ Complementary Tools**
- [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)
- [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)
- [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)
- [HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)
- [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 AUTEUR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com

## 📜 LICENCE
GPL-3.0 - Voir le fichier LICENSE pour plus de détails.

## 🛠️ BUILD & RUN

Utilisez la vérification de compilation sans versionnement avant une compilation de publication :

| Action | Windows | Linux / macOS |
|---|---|---|
| Vérification de compilation (sans modifier la version ni le CHANGELOG) | `build-test.bat` | `./build-test.sh` |
| Exécution / développement (si disponible) | `run*.bat` ou `dev*.bat` | `./run*.sh` ou `./dev*.sh` |

`build-test.bat` et `build-test.sh` compilent ou valident la pile du projet sans incrémenter `hydra-umc.project.json` ni modifier `CHANGELOG.md`. Ils peuvent uniquement créer les sorties normales du compilateur. Les scripts existants `build*.bat`, `build*.sh`, `run*` et `dev*` conservent leur comportement spécifique de versionnement ou d'exécution ; utilisez-les lorsque ce comportement est requis.
