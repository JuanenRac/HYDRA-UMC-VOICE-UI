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
* 🔀 **Ambiguitätsbewusste Klassifikation:** `classify_intent()` normalisiert Text (Unicode NFKC, Entfernen von Füllwörtern/Satzzeichen) und lehnt eine Transkription ab, die wirklich zu mehr als einem bekannten Befehl passt, statt stillschweigend einen zu erraten. *(implementiert; wird vom Watch-Voice-Gateway weiter unten verwendet)*
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
* **Warum das Watch-Gateway `classify_intent()` verwendet, nicht das
  alte `parse_intent()`.** `parse_intent()` bleibt für bestehende
  Aufrufer weiterhin "erste Übereinstimmung gewinnt" (unverändert,
  weiterhin so getestet), aber eine echte Transkription, die wirklich
  zu mehr als einem bekannten Befehl passt (z. B. enthält sowohl "stop"
  als auch "status"), ist eine echte, sicherheitsrelevante Mehrdeutigkeit
  für ein Gateway, dessen ganze Aufgabe darin besteht zu entscheiden, ob
  ein Bewegungsbefehl eine Bestätigung braucht - `classify_intent()`
  prüft jede Regel und meldet einen echten, eindeutig unterscheidbaren
  Mehrdeutigkeitsfall, statt ihn stillschweigend zu der Regel
  aufzulösen, die zufällig zuerst deklariert wurde.
* **Warum `normalize_text()` vor dem Abgleich Unicode NFKC anwendet.**
  Manche Speech-to-Text-Pipelines geben lateinische Buchstaben in voller
  Breite und andere Unicode-Kompatibilitätsformen aus - eigene
  Codepunkte, die sich von gewöhnlichem ASCII unterscheiden und daher
  für einen `\b...\b`-regulären Ausdruck nicht "das Wort" sind. NFKC
  reduziert sie zuerst auf ihr gewöhnliches Äquivalent, sodass ein
  Befehl, der semantisch mit einer bekannten Regel identisch ist,
  niemals nur wegen seiner Kodierung als ehrlicher Nicht-Treffer
  behandelt wird.

---

## 📂 VERZEICHNISSTRUKTUR

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/
│   ├── audio.py               # Echtes WAV-Laden + Sprachaktivitätserkennung per Energie
│   ├── intent.py               # Echter regelbasierter Absicht-/Entitäten-Parser + ambiguitätsbewusstes classify_intent()
│   ├── gateway.py               # Begrenztes Text-zu-Intent-Gateway, geteilt mit dem Watch-Cognitive-Flow
│   ├── http_service.py          # Kleine stdlib-HTTP-Grenze für den Watch-zu-Cognitive-Sprachpfad
│   └── main.py                  # Einstiegspunkt + echte Subcommands `analyze-audio`/`parse-intent`
├── tests/                    # Echte Tests: WAV-Fixtures, VAD, Intent-Regeln, Gateway, End-to-End-CLI
├── docs/                     # Dokumentation und Befehlskatalog
├── images/                   # Medien und Diagramme
├── deploy/
│   └── voice-ui.env.example  # Umgebungsvorlage für das lokale CM5-Gateway
├── systemd/
│   └── hydra-umc-voice-ui.service # systemd-Unit des lokalen CM5-Sprach-HTTP-Dienstes
├── tools/
│   ├── build_test.py         # Nicht-versionierender Build-Check
│   └── ci_validate.py        # Manifest/CHANGELOG/Docs-Validierung, von CI genutzt
├── build/                    # Lokale Build-Ausgabe (von git ignoriert)
├── pyproject.toml            # Paket-Metadaten (Version per Kilometerzähler-Inkrement)
├── bump_version.py           # Native Versionserhöhung im Kilometerzähler-Stil (von build.sh/.bat verwendet)
├── bump_manifest_version.py  # Synchronisiert die Version von hydra-umc.project.json mit der nativen (--sync)
├── build.sh / build.bat      # Erstellt das venv, installiert (mit Dev-Extras), prüft den Import, führt Tests aus
├── build-test.sh / build-test.bat # Nicht-mutierender Wrapper für tools/build_test.py (ändert weder Version noch Manifest noch CHANGELOG)
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
HYDRA-UMC-VOICE-UI v0.1.0
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

## 🎙️ WATCH-VOICE-GATEWAY (v0)

`python -m hydra_umc_voice_ui.main serve` stellt ein bewusst begrenztes lokales HTTP-Gateway für eine gekoppelte HYDRA-UMC-WATCH-Integration bereit: `GET /health` und `POST /v1/voice/turn`. Das Gateway validiert die typisierte Nutzlast `voice_turn`, verwendet den vorhandenen deterministischen Intent-Parser und liefert `assistant_reply`; es steuert keine Roboter-Hardware.

Die Loopback-Entwicklung kann ohne Token laufen. Eine Bindung außerhalb von Loopback benötigt `HYDRA_UMC_VOICE_UI_TOKEN` sowie einen passenden Header `Authorization: Bearer`. Diese API überträgt niemals Roh-Audio, und bewegungsbezogene Intents liefern immer `requiresConfirmation: true`.

Eine Transkription, die wirklich zu mehr als einem bekannten Befehl passt, wird mit einer echten, eindeutigen Antwort abgelehnt, statt stillschweigend zu einer Interpretation aufgelöst zu werden:

```json
// POST /v1/voice/turn
{"type": "voice_turn", "requestId": "watch-voice-001", "transcript": "stop the status check", "locale": "en-US"}

// -> {"type":"assistant_reply","requestId":"watch-voice-001","text":"That request matched more than one action (status, stop). Please rephrase it more specifically.","level":"ATTENTION","speak":true,"requiresConfirmation":false,"visualState":"clarification"}
```

Siehe [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) für den vollständigen Request-Vertrag und die Bereitstellungsgrenze, und [CLI_REFERENCE.md](docs/CLI_REFERENCE.md) für jedes reale `analyze-audio`/`parse-intent`/`serve`-Beispiel, aufgezeichnet vom installierten CLI.

## 🚀 FAHRPLAN
* **Phase 1:** VLA-Engine-Bereitstellung und multimodale Eingabeverarbeitung auf Hailo-10.
* **Phase 2:** Integration des semantischen Planers mit Schwarmverhaltensmodellen und Langzeitgedächtnis.
* **Phase 3:** Lokale Ausführung der Voice-UI mit niedriger Latenz und industrielle Geräuschunterdrückung.
* **Phase 4:** Mehrsprachige Unterstützung (Englisch, Spanisch, Deutsch, Französisch) und vollständige Integration mit Dashboard AI.

---

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage eigentlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Übergeordnetes Projekt**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrationsknoten für die Hailo-10-Cognitive-Pipeline (LLM-/VLA-/Sprach-Orchestrierung); das übergeordnete Projekt, dessen spezifische Stufe bzw. Verbraucher dieses Repository innerhalb seiner eigenen Cognitive-Pipeline ist.

**Geschwisterprojekte** — die übrigen Stufen/Verbraucher der eigenen Hailo-10-Cognitive-Pipeline von HYDRA-UMC-COGNITIVE-NODE
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur auf der Standardbibliothek basierende TF-IDF-Dokumentensuche über die eigenen Markdown-Dokumente dieses Ökosystems.

**Direkt verwandt**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter; eine weitere Sprachsteuerungsoberfläche des Ökosystems, neben diesem Dienst.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für das eingebaute 7"-DSI-Touchscreen, direkt auf dem CM5 eingebettet; eine weitere Sprachsteuerungsoberfläche des Ökosystems, neben diesem Dienst.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware & Plattform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — das physische Motherboard des Roboterarms: CM5-Host + Dual-Core-STM32H745, koordiniert bis zu 8 Werkzeugarme über CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag und die Sicherheitsschranke, gegen die jede Bridge ihre Befehle validiert.

*Kern-Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das reale Headless-Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarmleitstand (PySide6) für mehrere Server gleichzeitig, verpackt als eigenständige ausführbare Datei.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und einer gekoppelten Wear-OS-Begleit-App.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in STUDIOs eigenen Katalog überträgt.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen echten VDA-5050-MQTT-Publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit echtem GRBL-Status-/Steuerbyte-Zugriff.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem echten Boston-Dynamics-Spot-Befehlssender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Sicherheitskoordinator für Laserzellen, liest 3 echte Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Sicherungen.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer High-Level-Koordinator für den Leiterplattenfluss von OpenPnP Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsschranke für Moonraker/Klipper-3D-Drucker, mit echten gesicherten Job-Befehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Sicherheitskoordinator mit einem echten, träge importierten rclpy-ROS-2-Transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem echten MAVLink-Befehlssender.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Platinen, CAN-OTA plus Full-Chip-SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrationsknoten für die Hailo-8-Vision-Pipeline, mit einer echten stufenweisen Hardware-Bereitschaftsprüfung.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echte Registry für kompilierte Modelle mit Hailo-Architektur-/Prüfsummen-Safe-Load-Verifizierung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsschranke.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — echtes Position-Based-Visual-Servoing-Korrekturgesetz, sicherheitsgesteuert nach vorgelagertem Zonenstatus.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — echte Zonenverletzungsprüfung und E-STOP-Anforderung, mit erzwungener Kalibrierungsaktualität.

*Orchestrierung & Schwarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrationsknoten mit einem echten gRPC/Protobuf-Health-Report-Vertrag und einer Missions-Zustandsmaschine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Health-Watchdog mit Retry/Backoff und Identitäts-Mismatch-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet auf Multi-Zellen-Konvergenz.

*Digitaler Zwilling & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrationsknoten für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Sync-Vertrag.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — echte Hardware-in-the-Loop-Sicherheitsverriegelung, die Befehle zwischen Simulation und echter Hardware routet.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzenvalidierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO/COCO-Annotationsexport.

*Daten & Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Abfrage-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Basislinien-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über den DATALAKE-Verlauf, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN/WebSocket-Ingestion-Pipeline in DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrationsknoten, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Allowlist-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Binärprotokoll-Client-Session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Pro-Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-`/probe`- und `/current`-XML-Endpunkte mit Degraded-Mode-Ausgabe.

*Ergänzende Tools & Ökosystembetrieb*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit echten haptischen Alarmen und einem Sprach-Relay zum gekoppelten Telefon.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinenmontagegestell mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administratives Desktop-Tool, das jedes Repository in diesem Ökosystem entdeckt, klont und aktualisiert.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux-Desktop-Tool, das ein flashbereites CM5-Image baut, vorgeladen mit den aktuellsten Versionen des Ökosystems, mit Ersteinrichtungs-Konfiguration für WLAN/Benutzer/SSH im Stil von Raspberry Pi Imager.

---

## 📚 Dokumentation & Community

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.
- **[LICENSE.md](LICENSE.md)** — die eigene Lizenz dieses Projekts.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ
GPL-3.0 - Siehe LICENSE für Details.
