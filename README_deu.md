<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-VOICE-UI banner" width="100%">
</p>

# 🎙️ HYDRA-UMC-VOICE-UI

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🔊 Lokale hardwarebeschleunigte Speech-to-Action-Pipeline

<p align="left">
  <img src="https://img.shields.io/badge/Lizenz-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/STT-Whisper%20Lokal-FF6F00.svg" alt="STT">
  <img src="https://img.shields.io/badge/Plattform-Hailo--10-green.svg" alt="Hailo-10">
</p>

---

## 1. 🛠️ TECHNISCHER ÜBERBLICK

**HYDRA-UMC-VOICE-UI** ist die lokale Sprachinteraktionsschicht für das HYDRA-UMC-Ökosystem. Sie bietet eine Hochleistungs-STT- (Speech-to-Text) und TTS- (Text-to-Speech) Pipeline, die von der Hailo-10 NPU beschleunigt wird.

Sie ermöglicht es Bedienern, Robotermissionen zu steuern, den Systemstatus abzufragen und Audio-Feedback ohne jegliche Cloud-Konnektivität zu erhalten, was maximale Privatsphäre und null Latenz garantiert.

### Hauptmerkmale:
* 🎧 **Audio-Front-End (v0):** Echtes, rein stdlib-basiertes WAV-Laden und Sprachaktivitätserkennung per Energie-Schwellenwert. *(implementiert als echte Signalverarbeitungs-Primitive - nicht die Transkription selbst; siehe BUILD UND AUSFÜHRUNG unten)*
* 🎙️ **Edge STT:** Quantisierte Whisper-Modelle für eine fast sofortige Sprachtranskription. *(geplant - benötigt eine echte Modellabhängigkeit)*
* 📢 **Natürliches TTS:** Hochwertige Sprachsynthese für Systemwarnungen und Statusberichte. *(geplant)*
* 🧠 **NLU-Parser (v0):** Echte, regelbasierte Extraktion von Absicht/Entitäten aus erkanntem Text für den Semantic Planner. *(implementiert als Regex-Regeln über ein kleines echtes Befehlsvokabular - kein trainiertes ML-Modell; siehe BUILD UND AUSFÜHRUNG unten)*
* 🛡️ **Rauschunterdrückung:** Optimiert für industrielle Umgebungen mit hohem Umgebungslärm. *(geplant)*
* 👨‍👩‍👧 **Kind des Cognitive AI Node:** Läuft als einer von vier
  Schwesterdiensten unter [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)
  (neben VLA-Engine, Semantic-Planner und Docs-QA) und teilt sich das
  HydraOS-Image und die Modellgewichte des Elternteils, statt eigene
  Kopien vorzuhalten.
* 📦 **Kilometerzähler-Versionierung:** Jeder echte Build erhöht
  automatisch die Version in `pyproject.toml` (`bump_version.py`) - keine
  manuellen Versionsänderungen.

---

## 2. 🔄 VOICE-PIPELINE-ABLAUF

```mermaid
flowchart LR
    MIC["Mikrofoneingang"] --> STT["Whisper STT (Hailo-10)"]
    STT --> NLU["Semantischer Absichten-Parser"]
    NLU --> LOGIC["Kognitive Knotenlogik"]
    LOGIC --> TTS["TTS-Engine"]
    TTS --> SPK["Lautsprecherausgang"]
```

---

## 3. 🧱 ARCHITEKTUR & DESIGNENTSCHEIDUNGEN

Dieses Repository ist ein **Kind** der Cognitive AI Node-Familie - sein
Elternteil, [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE),
besitzt das gemeinsam genutzte HydraOS-Image und die quantisierten
Modellgewichte und bindet diesen Dienst in seiner `docker-compose.yml`
neben seinen drei Geschwistern (VLA-Engine, Semantic-Planner, Docs-QA)
ein:

* **Warum dieses Kind keine eigene Hardware/Firmware/`os/`/`models/`
  hat.** Es läuft vollständig auf dem CM5 + Hailo-10 M.2-Modul, das
  bereits dem Elternteil gehört - Modellgewichte und HydraOS-Image an
  einer zentralen Stelle zu halten vermeidet vier abweichende, mehrere
  Gigabyte große Kopien innerhalb der Familie.
* **Warum ein `src/`-Layout.** Trennt das installierbare Paket
  (`hydra_umc_voice_ui`) vom Tooling im Repo-Root (`bump_version.py`)
  und entspricht dem Layout aller anderen Python-Projekte im Ökosystem.
* **Warum der Einstiegspunkt heute nur Identität/Version/Rolle
  ausgibt.** Dies ist die Andamiaje- (Gerüst-) Phase: zu beweisen, dass
  sich das Paket auf der tatsächlichen Ziel-Python-Version sauber
  installieren, kompilieren und importieren lässt, ist Voraussetzung,
  bevor echte STT/TTS-Pipeline-Logik hinzugefügt wird, und hält diese
  spätere Arbeit von Packaging-Fragen getrennt.
* **Wie sich das in den Rest des Ökosystems einfügt.** Dieser Dienst ist
  der freihändige Einstiegspunkt in den gesamten Cognitive AI Node:
  erkannte Absicht fließt zu seinem Geschwister
  HYDRA-UMC-SEMANTIC-PLANNER, und er fungiert neben HYDRA-UMC-STUDIO und
  HYDRA-UMC-DSI als Sprachsteuerungs-Oberfläche.
* **Warum `audio.py` `wave`/`array` statt numpy verwendet.** Das
  Dekodieren von 16-Bit-PCM und eine echte Energie-Schwellenwert-VAD
  brauchen nichts über das hinaus, was die stdlib bereits bietet - v0
  ohne Abhängigkeiten zu halten bedeutet, dass das echte Audio-Front-End
  überall läuft, wo Python läuft, noch bevor irgendeine
  Hailo-10-spezifische STT-Abhängigkeit installiert ist.
* **Warum `intent.py` echte Regex-Regeln sind, kein trainiertes
  NLU-Modell.** Ein kleines, echtes Befehlsvokabular
  (start/stop/status/go home) wird heute vollständig und ehrlich durch
  Regeln abgedeckt - dieselbe Überlegung wie der echte TF-IDF-Index des
  Geschwisterprojekts HYDRA-UMC-DOCS-QA anstelle eines
  Embedding-Modells: ein echter, testbarer Kern jetzt, den ein
  künftiger ML-basierter Klassifikator hinter demselben
  `parse_intent()`-Vertrag ersetzen kann, sobald erkannte Sprache mehr
  als dieses v0-Vokabular abdecken muss.
* **Warum nicht übereinstimmendes Audio/Text einen ehrlichen
  Fehlschlag liefert, keine Vermutung.** `detect_voice_segments()`
  liefert für Stille eine leere Liste, und `parse_intent()` liefert
  `None` für Text außerhalb seines Regelsatzes - v0 hat kein
  Rückfallmodell, erfindet also niemals ein Segment oder eine Absicht,
  die es tatsächlich nicht erkannt hat.

---

## 📂 VERZEICHNISSTRUKTUR

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/
│   ├── audio.py               # Echtes WAV-Laden + Sprachaktivitätserkennung per Energie
│   ├── intent.py               # Echter regelbasierter Absicht-/Entitäten-Parser
│   └── main.py                  # Einstiegspunkt + echte Subcommands `analyze-audio`/`parse-intent`
├── tests/                    # Echte Tests: WAV-Fixtures, VAD, Intent-Regeln, End-to-End-CLI
├── docs/                     # Dokumentation und Befehlskatalog
├── images/                   # Medien und Diagramme
├── scripts/                  # Utility-Skripte
├── build/                    # Lokale Build-Ausgabe (von git ignoriert)
├── pyproject.toml            # Paket-Metadaten (Version 0.0.5, Kilometerzähler-Inkrement)
├── bump_version.py           # Versionserhöhung im Kilometerzähler-Stil (von build.sh/.bat verwendet)
├── build.sh / build.bat      # Erstellt das venv, installiert (mit Dev-Extras), prüft den Import, führt Tests aus
└── run.sh / run.bat          # Führt den Einstiegspunkt aus (leitet Argumente weiter, z. B. `analyze-audio`)
```

> **Hinweis:** `hardware/` und `firmware/` wurden entfernt - dieser Knoten
> läuft auf einem bereits vorhandenen CM5 + Hailo-10 M.2 Modul ohne
> eigenes Hardware-/Firmware-Design. Auch `os/` und `models/` wurden
> entfernt - das HydraOS-Image und die gemeinsam genutzten
> Hailo-10-Modellgewichte befinden sich im übergeordneten Projekt
> `HYDRA-UMC-COGNITIVE-NODE`, an das dieses Projekt als Dienst angebunden
> wird (siehe dessen `docker-compose.yml`).

---

## ⚙️ BUILD UND AUSFÜHRUNG

Erfordert Python >= 3.10.

```bash
# Linux / macOS / Git Bash
./build.sh   # erstellt .venv, installiert das Paket (editable), prüft den Import
./run.sh     # führt den Einstiegspunkt aus

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` erhöhen die Version (Kilometerzähler-Stil, siehe
`bump_version.py`) vor jedem echten Build und führen die echte Testsuite
aus (`pytest tests/`). Erwartete Ausgabe eines `run.sh` ohne Argumente:

```text
HYDRA-UMC-VOICE-UI v0.0.5
Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free robotic mission control.
```

Die echten Subcommands analysieren eine WAV-Datei oder verarbeiten
bereits transkribierten Text:

```bash
./run.sh analyze-audio recordings/command.wav
./run.sh parse-intent "start mission alpha"

# Windows
run.bat analyze-audio recordings\command.wav
run.bat parse-intent "status of robot 3"
```

### 🩺 Fehlerbehebung

* **`python: Befehl nicht gefunden` / der Build schlägt bei Schritt 1
  fehl.** Erfordert Python >= 3.10 im `PATH`. Unter Windows von
  [python.org](https://python.org) installieren und bei der Installation
  "Add to PATH" ankreuzen; unter Linux/macOS heißt es meist `python3`.
* **`build.sh` kann das venv nicht aktivieren.** `python3 -m venv .venv`
  legt das Aktivierungsskript je nach Plattform an anderer Stelle ab:
  `.venv/bin/activate` unter Linux/macOS, `.venv/Scripts/activate` unter
  Windows (auch bei einem Windows-Python-venv, das aus Git Bash heraus
  verwendet wird). `build.sh` prüft bereits beide Pfade - schlägt es
  weiterhin fehl, `.venv/` löschen und `./build.sh` erneut ausführen, um
  es von Grund auf neu zu erstellen.
* **`pip install -e .` schlägt fehl.** Meist wegen eines veralteten
  `.venv/`. Den Ordner `.venv/` löschen und `./build.sh`/`build.bat`
  erneut ausführen, um ihn neu zu erstellen.
* **`import OK` erscheint nie.** Bedeutet, dass `python -c "import
  hydra_umc_voice_ui"` selbst fehlgeschlagen ist - mit aktivem venv
  erneut ausführen, um den echten Traceback zu sehen.

---

## 🚀 ROADMAP
* **Phase 1:** VLA-Engine-Bereitstellung und multimodale Eingabeverarbeitung auf Hailo-10.
* **Phase 2:** Integration des semantischen Planers mit Schwarmverhaltensmodellen und Langzeitgedächtnis.
* **Phase 3:** Lokale Ausführung der Voice-UI mit niedriger Latenz und industrielle Geräuschunterdrückung.
* **Phase 4:** Mehrsprachige Unterstützung (Englisch, Spanisch, Deutsch, Französisch) und vollständige Integration mit Dashboard AI.

---

## 🔗 VERWANDTE PROJEKTE

Dieses Projekt ist Teil eines größeren Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D), das Firmware, Steuerungssoftware, KI-Knoten und Flotten-Tooling umfasst.

### Direkt mit diesem Dienst verbunden

- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** / **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — weitere Sprachsteuerungs-Oberflächen des Ökosystems.

### Rest des Ökosystems

**HYDRA-UMC-Plattform** — die Multi-Roboter-Mikrofabrikzelle
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — das Motherboard selbst: Raspberry Pi CM5 Host + dualer STM32H745 Echtzeit-Co-Prozessor, der bis zu 8 verteilte Roboterarme über CAN-OTA/SPI-OTA orchestriert.
- **[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — headless Express/WebSocket-Backend, das den Roboterzustand besitzt.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — Android-Steuerungs-App für HYDRA-UMC.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App für HYDRA-UMC.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarm-Kommandozentrale.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor.

**URTC-Plattform** — der Werkzeugkopf-Controller, den jeder HYDRA-UMC-Roboterarm trägt
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller, Firmware.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-Tool für CAN-OTA + SWD/JTAG-Flashing.
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Tool für Live-CAN-Bus-Diagnose.
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu den beiden Desktop-Tools oben.

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

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com

## 📜 LIZENZ
GPL-3.0 - Siehe LICENSE für Details.
