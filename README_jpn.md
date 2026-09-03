<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-VOICE-UI banner" width="100%">
</p>

# 🎙️ HYDRA-UMC-VOICE-UI

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | 🇯🇵 <b>日本語</b></p>

### 🔊 ローカルでハードウェアアクセラレーションされる音声-動作パイプライン

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/STT-Whisper%20Local-FF6F00.svg" alt="STT">
  <img src="https://img.shields.io/badge/Platform-Hailo--10-green.svg" alt="Hailo-10">
</p>

---

## 1. 🛠️ 技術概要

**HYDRA-UMC-VOICE-UI** は、HYDRA-UMC エコシステムのローカル音声インタ
ラクション層です。Hailo-10 NPU によって加速される高性能な STT（音声認識）
と TTS（音声合成）のパイプラインを提供します。

これにより、オペレーターはクラウド接続なしにロボットミッションを制御し、
システムステータスを照会し、音声フィードバックを受け取ることができ、
最大限のプライバシーとゼロレイテンシーを実現します。

### 主な機能：
* 🎧 **オーディオフロントエンド（v0）：** 標準ライブラリのみによる実際の WAV 読み込みと、エネルギー閾値による音声活動検出。*（実際の信号処理プリミティブとして実装済み——文字起こし自体ではありません。下記の「ビルドと実行」を参照）*
* 🎙️ **エッジ STT：** ほぼ瞬時の音声書き起こしのための量子化された Whisper モデル。*（計画中——実際のモデル依存関係が必要です）*
* 📢 **自然な TTS：** システムアラートとステータスレポート向けの高品質な音声合成。*（計画中）*
* 🧠 **NLU パーサー（v0）：** 認識されたテキストからの、ルールベースによる実際の意図/エンティティ抽出。Semantic Planner に提供します。*（小さな実際のコマンド語彙に対する正規表現ルールとして実装済み——学習済み ML モデルではありません。下記の「ビルドと実行」を参照）*
* 🔀 **あいまいさを考慮した分類：** `classify_intent()` はテキストを正規化し（Unicode NFKC、フィラー語/句読点の除去）、複数の既知コマンドに本当に一致する文字起こしを、黙って1つに絞り込むのではなく拒否します。*（実装済み；下記の Watch 音声ゲートウェイで使用されます）*
* 🛡️ **ノイズキャンセリング：** 高い環境ノイズを伴う産業環境向けに最適化。*（計画中）*
* 👨‍👩‍👧 **認知 AI ノードの子プロジェクト：**
  [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) の下で 4 つの兄弟サービスの 1 つとして動作します（VLA-Engine、Semantic-Planner、Docs-QA と並んで）。独自のコピーを保持するのではなく、親プロジェクトの HydraOS イメージとモデルの重みを共有します。
* 📦 **オドメーター式バージョン管理：** 実際のビルドのたびに
  `pyproject.toml` 自身のバージョンが自動的に増加します
  （`bump_version.py`）——手動でのバージョン編集は不要です。

---

## 2. 🔄 音声パイプラインフロー

```mermaid
flowchart LR
    MIC["Microphone Input"] --> STT["Whisper STT (Hailo-10)"]
    STT --> NLU["Semantic Intent Parser"]
    NLU --> LOGIC["Cognitive Node Logic"]
    LOGIC --> TTS["TTS Engine"]
    TTS --> SPK["Speaker Output"]
```

---

## 3. 🧱 アーキテクチャと設計上の決定

本リポジトリは Cognitive AI Node ファミリーの**子プロジェクト**です——
親プロジェクトである [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) が共有の HydraOS イメージと量子化モデルの重みを保持し、本サービスを他の 3 つの兄弟プロジェクト（VLA-Engine、Semantic-Planner、Docs-QA）とともに `docker-compose.yml` に接続します：

* **本子プロジェクトに独自のハードウェア/ファームウェア/`os/`/`models/` がない理由。** 親プロジェクトが既に保有する CM5 + Hailo-10 M.2 モジュール上で完全に動作します——モデルの重みと HydraOS イメージを 1 か所に集約することで、ファミリー全体で数 GB にも及ぶモデルの重みが 4 つの食い違ったコピーとして存在することを避けられます。
* **`src/` レイアウトを採用した理由。** インストール可能なパッケージ（`hydra_umc_voice_ui`）をリポジトリルートのツール（`bump_version.py`）から分離し、エコシステム内の他のすべての Python プロジェクトで使用されているレイアウトと一致させるためです。
* **エントリポイントが今日は身元/バージョン/役割のみを表示する理由。** これは足場（スキャフォールディング）段階です：実際のターゲット Python バージョン上で、本パッケージが正しくインストール・コンパイルされ、問題なくインポートできることを証明することが、後で実際の STT/TTS パイプラインロジックを追加するための前提条件であり、その後の作業をパッケージングの懸念から切り離しておきます。
* **エコシステムの他の部分との関係。** 本サービスは、Cognitive AI Node 全体へのハンズフリーなエントリポイントです：認識された意図は兄弟プロジェクトである HYDRA-UMC-SEMANTIC-PLANNER に流れ、HYDRA-UMC-STUDIO や HYDRA-UMC-DSI と並んで音声制御インターフェースとして機能します。
* **`audio.py` が numpy ではなく `wave`/`array` を使う理由。** 16 ビット PCM のデコードと実際のエネルギー閾値 VAD は、標準ライブラリがすでに提供するもの以外何も必要としません——v0 を依存関係なしに保つことで、実際のオーディオフロントエンドは、Hailo-10 固有の STT 依存関係がインストールされる前でも、Python が動くあらゆる場所で動作します。
* **`intent.py` が学習済み NLU モデルではなく実際の正規表現ルールである理由。** 小さな実際のコマンド語彙（start/stop/status/go home）は、今日ルールによって完全かつ正直にカバーされています——これは兄弟プロジェクトである HYDRA-UMC-DOCS-QA が埋め込みモデルではなく実際の TF-IDF インデックスを使う理由と同じです：認識された音声がこの v0 語彙以上をカバーする必要が出てきたときに、将来 ML ベースの分類器が同じ `parse_intent()` 契約の背後で置き換えられる、実際に機能するテスト可能なカーネルを今持っているということです。
* **一致しないオーディオ/テキストが推測ではなく正直な失敗を返す理由。** `detect_voice_segments()` は無音に対して空リストを返し、`parse_intent()` はルールセット外のテキストに対して `None` を返します——v0 にはフォールバックモデルがないため、実際には検出していないセグメントや意図を捏造することは決してありません。
* **Watch ゲートウェイが旧来の `parse_intent()` ではなく `classify_intent()` を使う理由。** 既存の呼び出し元に対しては `parse_intent()` は引き続き「最初に一致したものが勝つ」動作のまま変更されず、これまで通りテストされます。しかし、複数の既知コマンドに本当に一致する実際の文字起こし（例えば "stop" と "status" の両方を含む場合）は、運動コマンドに確認が必要かどうかを判断することが全ての役割であるゲートウェイにとって、実在の、安全性に関わるあいまいさです——`classify_intent()` はすべてのルールをチェックし、たまたま最初に宣言されたルールへ黙って解決するのではなく、実在の、明確に区別されるあいまいなケースを報告します。
* **`normalize_text()` がマッチングの前に Unicode NFKC を適用する理由。** 一部の音声認識パイプラインは全角ラテン文字やその他の互換 Unicode 形式を出力します——これらは通常の ASCII とは異なるコードポイントであり、`\b...\b` 正規表現にとっては「その単語」とは見なされません。NFKC はまずそれらを通常の等価な形式に変換するため、既知のルールと意味的に同一のコマンドが、単にエンコードの違いだけを理由に正直な不一致として扱われることはありません。

---

## 📂 リポジトリ構成

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/
│   ├── audio.py               # 実際の WAV 読み込み + エネルギーによる音声活動検出
│   ├── intent.py               # 実際のルールベース意図/エンティティパーサー + あいまいさを考慮した classify_intent()
│   ├── gateway.py               # Watchの認知フローが共有する、範囲を限定したテキスト→意図ゲートウェイ
│   ├── http_service.py          # Watch→認知の音声経路のための小さなstdlib HTTP境界
│   └── main.py                  # エントリポイント + 実際の `analyze-audio`/`parse-intent` サブコマンド
├── tests/                    # 実際のテスト：WAV フィクスチャ、VAD、意図ルール、gateway、エンドツーエンド CLI
├── docs/                     # ドキュメントとコマンドカタログ
├── images/                   # メディアと図表
├── deploy/
│   └── voice-ui.env.example  # ローカルCM5ゲートウェイの環境テンプレート
├── systemd/
│   └── hydra-umc-voice-ui.service # ローカルCM5音声HTTPサービスのsystemdユニット
├── tools/
│   ├── build_test.py         # バージョンを増やさないビルドチェック
│   └── ci_validate.py        # CI が使用するマニフェスト/CHANGELOG/ドキュメント検証
├── build/                    # ローカルビルド出力（git 管理外）
├── pyproject.toml            # パッケージメタデータ（オドメーター式バージョン増加）
├── bump_version.py           # ネイティブバージョンのオドメーター式インクリメント（build.sh/.bat が使用）
├── bump_manifest_version.py  # hydra-umc.project.json のバージョンをネイティブ版と同期(--sync)
├── build.sh / build.bat      # venv 作成、インストール（dev エクストラ付き）、インポート検証、テスト実行
└── run.sh / run.bat          # エントリポイントを実行（引数を転送、例：`analyze-audio`）
```

> **注：** `hardware/` と `firmware/` は省略されています——本ノードは
> 既存の CM5 + Hailo-10 M.2 モジュール上で動作し、独自のハードウェア/
> ファームウェア設計を持ちません。`os/` と `models/` も省略されています
> ——HydraOS イメージと共有される Hailo-10 モデルの重みは、親プロジェクト
> `HYDRA-UMC-COGNITIVE-NODE` に存在し、本プロジェクトはサービスとして
> それに接続します（その `docker-compose.yml` を参照）。

---

## ⚙️ ビルドと実行

Python >= 3.10 が必要です。

```bash
# Linux / macOS / Git Bash
./build.sh   # .venv を作成し、パッケージを（editable モードで）インストールし、インポートを検証します
./run.sh     # エントリポイントを実行します

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` は、実際の各ビルドの前にバージョンを増加させ
（オドメーター方式、`bump_version.py` を参照）、実際のテストスイートを
実行します（`pytest tests/`）。引数なしの `run.sh` の予期される出力：

```text
HYDRA-UMC-VOICE-UI v0.1.0
Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free robotic mission control.
```

実際のサブコマンドは、WAV ファイルを分析するか、すでに文字起こしされた
テキストを処理します：

```bash
./run.sh analyze-audio recordings/command.wav
./run.sh parse-intent "start mission alpha"

# Windows
run.bat analyze-audio recordings\command.wav
run.bat parse-intent "status of robot 3"
```

### 🩺 トラブルシューティング

* **`python: command not found` / ビルドがステップ 1 で失敗する。** `PATH` 上に Python >= 3.10 が必要です。Windows では [python.org](https://python.org) からインストールし、セットアップ中に「Add to PATH」がチェックされていることを確認してください。Linux/macOS では通常 `python3` という名前が使われます。
* **`build.sh` が venv をアクティブ化できない。** `python3 -m venv .venv` は、プラットフォームごとに異なる場所にアクティベートスクリプトを配置します：Linux/macOS では `.venv/bin/activate`、Windows（Git Bash から使用される Windows Python venv でも同様）では `.venv/Scripts/activate`。`build.sh` は既に両方のパスをチェックしています——それでも失敗する場合は、`.venv/` を削除して `./build.sh` を再実行し、ゼロから再構築してください。
* **`pip install -e .` が失敗する。** 通常は `.venv/` が古くなっていることが原因です。`.venv/` フォルダを削除して `./build.sh`/`build.bat` を再実行し、再作成してください。
* **`import OK` が一度も表示されない。** `python -c "import hydra_umc_voice_ui"` 自体が失敗したことを意味します——venv がアクティブな状態で再実行し、実際のトレースバックを確認してください。

---

## 🎙️ WATCH 音声ゲートウェイ（v0）

`python -m hydra_umc_voice_ui.main serve` は、ペアリングされた HYDRA-UMC-WATCH 統合用に意図的に制限されたローカル HTTP ゲートウェイを公開します。エンドポイントは `GET /health` と `POST /v1/voice/turn` です。ゲートウェイは型付き `voice_turn` ペイロードを検証し、既存の決定論的なインテントパーサーを使用して `assistant_reply` を返します。ロボットハードウェアを制御するものではありません。

ループバック開発はトークンなしで実行できます。ループバック以外へのバインドには `HYDRA_UMC_VOICE_UI_TOKEN` と一致する `Authorization: Bearer` ヘッダーが必要です。この API が生の音声を転送することはなく、移動に関係するインテントは常に `requiresConfirmation: true` を返します。

複数の既知コマンドに本当に一致する文字起こしは、単一の解釈へ黙って解決されるのではなく、実在の、明確に区別される応答とともに拒否されます：

```json
{"transcript": "stop the status check"}
// -> {"text": "That request matched more than one action (status, stop). Please rephrase it more specifically.", "requiresConfirmation": false, "intent": null}
```

リクエスト契約とデプロイ境界については [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) を参照してください。

## 🚀 ロードマップ
* **フェーズ 1：** Hailo-10 上での VLA エンジンのデプロイとマルチモーダル入力処理。
* **フェーズ 2：** 意味プランナーと群行動モデルおよび長期記憶の統合。
* **フェーズ 3：** 音声 UI の低遅延ローカル実行と産業用ノイズキャンセリング。
* **フェーズ 4：** 多言語サポート（英語、スペイン語、ドイツ語、フランス語）と Dashboard AI との完全統合。

---

## 🔗 関連プロジェクト

本プロジェクトは、同じ作者(JuanenRac / Electro Hobby 3D)による HYDRA-UMC ロボティクスエコシステムの一部です。リクエストが実はこの中のどれかについてのものである可能性があるため、知っておく価値があります。

**親プロジェクト**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Hailo-10 コグニティブパイプライン(LLM/VLA/音声オーケストレーション)の統合ハブ。本リポジトリは、その自身のコグニティブパイプライン内における特定の段階・消費者として、この親の一部を成す。

**兄弟プロジェクト** —— HYDRA-UMC-COGNITIVE-NODE 自身の Hailo-10 コグニティブパイプラインにおける他の段階・消費者
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — MCU エラーコードに対する、実際のルールベースのタスク分解と意味的エラー復旧。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — Vision-Language-Action モデル向けの、実際のアクショントークンのエンコード/デコードと軌道生成。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — このエコシステム自身の Markdown ドキュメントに対する、標準ライブラリのみの実際の TF-IDF 文書検索。

**直接関連**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — リアルタイムのマルチロボット 3D 可視化を備えたウェブ制御ダッシュボード。本サービスと並ぶ、エコシステムのもう一つの音声制御サーフェス。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 本体搭載の 7 インチ DSI タッチスクリーン向けネイティブタッチ UI、CM5 自体に組み込み。本サービスと並ぶ、エコシステムのもう一つの音声制御サーフェス。

**エコシステムの他のプロジェクト**

*コアハードウェア&プラットフォーム*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 実際のロボットアームのマザーボード——CM5 ホスト + デュアルコア STM32H745、CAN-OTA/SPI-OTA 経由で最大 8 本のツールアームを統括。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — CM5 向けの再現可能な Raspberry Pi OS プロダクト層——読み取り専用エージェント、検証済み設定/プロファイル、WiFi 初回接続プロビジョニング。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — すべてのブリッジが自身のコマンドを検証する共有 JSON-Schema 契約と安全ゲートの境界。

*コアバックエンド&クライアント*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — すべての制御クライアントが実際に通信する、本物のヘッドレスバックエンド(REST/WebSocket)。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 複数のサーバーを同時に扱えるデスクトップ(PySide6)スウォームコマンドセンター、スタンドアロン実行ファイルとしてパッケージ化。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 生体認証ログインとペアリングされた Wear OS コンパニオンを備えたネイティブ Android 制御アプリ。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — リアルタイム WebSocket 同期を備えた iOS/iPadOS 制御アプリ(Flutter)。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 完成したモデルを STUDIO 自身のカタログへ送信するデスクトップ用グラフィカル URDF 作成/編集ツール。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 実際の VDA 5050 MQTT パブリッシャーによる AGV/AMR フリートの調整境界。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 実際の GRBL ステータス/制御バイトへのアクセスを持つ、CNC セルの高レベルコーディネーター。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 実際の Boston Dynamics Spot コマンド送信機能を持つ、脚型/ヒューマノイドドロイドの調整境界。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 実際のキー/筐体/インターロック GPIO セーフガード 3 系統を読み取る、レーザーセルの安全コーディネーター。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — OpenPnP ピックアンドプレースの基板フローを安全に統括する高レベルコーディネーター。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 実際にゲート制御されたジョブコマンドを持つ、Moonraker/Klipper 3D プリンター向けの安全な調整境界。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 実際の遅延インポート rclpy ROS 2 トランスポートを持つ安全コーディネーター。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 実際の MAVLink コマンド送信機能を持つ、カメラ搭載 UAV の調整境界。

*URTC ツールプラットフォーム*
- **[URTC](https://github.com/JuanenRac/URTC)** — 物理的な Universal Robot Tool Controller 基板向けファームウェア、CAN バス経由の 25 以上のツールプロファイル。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — URTC 基板用のデスクトップ GUI 書き込みツール、CAN-OTA およびフルチップ SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — URTC 基板向けのデスクトップ CAN バスライブ診断ツール、ツールプロファイルごとに 1 パネル。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — Web Serial API を使ったブラウザベースの URTC-TESTER の代替、ローカルインストール不要。

*ビジョン AI ノード(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Hailo-8 ビジョンパイプラインの統合ハブ、段階ごとの実際のハードウェア準備状況チェック付き。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — Hailo アーキテクチャ/チェックサムによる安全読み込み検証を備えた、実際のコンパイル済みモデルレジストリ。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 実際の HailoRT 統合境界を持つ、実際の GStreamer パイプライン + MediaMTX 設定生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 上流のゾーン状態に応じて安全ゲート制御される、実際の Position-Based Visual Servoing 補正則。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — キャリブレーションの鮮度を強制する、実際のゾーン侵入チェックと E-STOP 要求。

*オーケストレーション&スウォーム*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 実際の gRPC/Protobuf ヘルスレポート契約とミッションステートマシンを持つ統合ハブ。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 実際の HTTP API 上に構築された、優先度ベースの実際のジョブキュー(重複排除付き)。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — リトライ/バックオフとアイデンティティ不一致検出を備えた、実際の gRPC ベースのフリートヘルスウォッチドッグ。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 実際の障害物/ワークスペース衝突検証を備えた、実際の RRT ベースの 3D 経路プランナー。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 複数セルの収束についてプロパティテストされた、実際の CRDT LWW-Element-Map 状態同期。

*デジタルツイン&シミュレーション*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 実際のバージョン互換性同期契約を持つ、デジタルツインエンジンの統合ハブ。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — シミュレーションと実際のハードウェアの間でコマンドをルーティングする、実際のハードウェア・イン・ザ・ループ安全インターロック。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 実際の URDF サブセットに対する、実際の順運動学と関節限界検証。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — YOLO/COCO アノテーションのエクスポート機能を持つ、実際のプロシージャル 2D シーンジェネレーター。

*データ&分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 実際の取り込み/クエリ HTTP API を備えた、実際の sqlite3 ベースの時系列ストア。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — ドリフト監視を備えた、実際の FFT + 統計ベースラインによる異常検知器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — DATALAKE の履歴に対する実際の OEE/稼働率計算、再現可能な CSV エクスポート付き。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — シーケンス重複排除機能を備えた、DATALAKE への実際の CAN/WebSocket 取り込みパイプライン。

*産業用ゲートウェイ*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 実際のコマンド許可リスト/バックプレッシャー層を持つ、産業用プロトコルへ中継する統合ハブ。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 実際のバイナリプロトコルクライアントセッションで検証された、実際の OPC-UA アドレス空間。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — クライアント単位のオプション認証とトピック ACL を備えた、実際の MQTT ブローカー。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 縮退モード出力を備えた、実際の MTConnect `/probe` および `/current` XML エンドポイント。

*補完ツール&エコシステム運用*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 誠実な統計フォールバックを備えた、DATALAKE/ANOMALY-DETECTOR 上のスマートサマリーと異常ハイライトパネル。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 実際の安定した終了コード契約を持つフリート CLI、HYDRA-UMC-SERVER 自身の API の本物のライブクライアント。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 実際の触覚アラートとペアリングされたスマートフォンへの音声リレーを備えた WearOS コンパニオンアプリ。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 実際の工具 ID デコードと Smart Idle 予熱ロジックを備えた、基板搭載ラック用ファームウェア。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — サーマル/RGB 検査ツールヘッド向けの、ファームウェアと実際の Python ビジョンコンパニオン。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — このエコシステム内のすべてのリポジトリを検出・クローン・更新する、管理用デスクトップツール。

---

## 📚 ドキュメント & コミュニティ

- **[CONTRIBUTING.md](CONTRIBUTING.md)** —— プルリクエストのための技術スタックとコーディング指針。
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** —— このコミュニティで期待される行動規範。
- **[SECURITY.md](SECURITY.md)** —— 脆弱性の報告方法と、このプロジェクトの実際のセキュリティ重点領域。
- **[SUPPORT.md](SUPPORT.md)** —— 質問の投稿先とバグの報告先。
- **[LICENSE.md](LICENSE.md)** —— このプロジェクト自身のライセンス。

## 👤 作者
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 ライセンス
GPL-3.0 —— 詳細は LICENSE を参照してください。
