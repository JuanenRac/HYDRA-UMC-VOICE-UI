<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-VOICE-UI banner" width="100%">
</p>

# 🎙️ HYDRA-UMC-VOICE-UI

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🔊 本地硬件加速的语音转动作流水线

<p align="left">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/STT-Whisper%20Local-FF6F00.svg" alt="STT">
  <img src="https://img.shields.io/badge/Platform-Hailo--10-green.svg" alt="Hailo-10">
</p>

---

## 1. 🛠️ 技术概述

**HYDRA-UMC-VOICE-UI** 是 HYDRA-UMC 生态系统的本地语音交互层。它提供由
Hailo-10 NPU 加速的高性能 STT（语音转文本）和 TTS（文本转语音）流水线。

它使操作员能够在没有任何云端连接的情况下控制机器人任务、查询系统状态并
接收音频反馈，确保最大程度的隐私和零延迟。

### 关键特性：
* 🎧 **音频前端（v0）：** 真实的、仅依赖标准库的 WAV 加载与基于能量阈值的语音活动检测。*（已实现为真实的信号处理原语——并非转录本身；见下方“构建与运行”）*
* 🎙️ **边缘端 STT：** 用于近乎即时语音转录的量化 Whisper 模型。*（计划中——需要真实的模型依赖）*
* 📢 **自然 TTS：** 用于系统告警和状态报告的高质量语音合成。*（计划中）*
* 🧠 **NLU 解析器（v0）：** 基于规则的真实意图/实体提取，作用于识别出的文本，供语义规划器使用。*（已实现为对一个小型真实命令词汇表的正则规则——并非经过训练的 ML 模型；见下方“构建与运行”）*
* 🔀 **歧义感知分类：** `classify_intent()` 会对文本进行规范化（Unicode NFKC、去除填充词/标点），并拒绝真正匹配多个已知命令的转录文本，而不是悄悄地猜一个。*（已实现；供下方 Watch 语音网关使用）*
* 🛡️ **噪声消除：** 针对高环境噪声的工业环境进行优化。*（计划中）*
* 👨‍👩‍👧 **认知 AI 节点子项目：** 作为
  [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) 下 4 个同级服务之一运行（与 VLA-Engine、Semantic-Planner 和 Docs-QA 并列），共享父项目的 HydraOS 镜像和模型权重，而非各自保留独立副本。
* 📦 **里程表式版本管理：** 每次真实构建都会自动递增 `pyproject.toml`
  自身的版本号（`bump_version.py`）——无需手动编辑版本号。

---

## 2. 🔄 语音流水线流程

```mermaid
flowchart LR
    MIC["Microphone Input"] --> STT["Whisper STT (Hailo-10)"]
    STT --> NLU["Semantic Intent Parser"]
    NLU --> LOGIC["Cognitive Node Logic"]
    LOGIC --> TTS["TTS Engine"]
    TTS --> SPK["Speaker Output"]
```

---

## 3. 🧱 架构与设计决策

本仓库是 Cognitive AI Node 系列的**子项目**——其父项目
[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) 拥有共享的 HydraOS 镜像和量化模型权重，并将本服务与其另外 3 个同级项目（VLA-Engine、Semantic-Planner、Docs-QA）一同接入 `docker-compose.yml`：

* **为何本子项目没有自己的硬件/固件/`os/`/`models/`。** 它完全运行在父项目已拥有的 CM5 + Hailo-10 M.2 模块上——将模型权重和 HydraOS 镜像集中保存在一处，可避免整个项目族中出现四份互不一致的、动辄数 GB 的副本。
* **为何采用 `src/` 布局。** 使可安装的包（`hydra_umc_voice_ui`）与仓库根目录的工具（`bump_version.py`）分离，与生态系统中其他每个 Python 项目所使用的布局保持一致。
* **为何入口点今天只打印身份/版本/角色。** 这是脚手架（scaffolding）阶段：证明该包在实际目标 Python 版本上能够正确安装、编译并被导入，是后续添加真正的 STT/TTS 流水线逻辑的前提条件，并使那部分后续工作与打包相关的问题相互隔离。
* **这如何融入生态系统的其余部分。** 本服务是进入整个 Cognitive AI Node 的免提入口点：识别出的意图流向其同级项目 HYDRA-UMC-SEMANTIC-PLANNER，并与 HYDRA-UMC-STUDIO 和 HYDRA-UMC-DSI 一同充当语音控制界面。
* **为何 `audio.py` 使用 `wave`/`array` 而非 numpy。** 16 位 PCM 解码和真实的能量阈值 VAD 除了标准库已经提供的之外，不需要任何东西——让 v0 保持零依赖，意味着真实的音频前端可以在任何运行 Python 的地方工作，甚至在安装任何 Hailo-10 专用 STT 依赖之前就能运行。
* **为何 `intent.py` 是真实的正则规则，而非经过训练的 NLU 模型。** 一个小型真实的命令词汇表（start/stop/status/go home）如今已被规则完全且诚实地覆盖——这与兄弟项目 HYDRA-UMC-DOCS-QA 使用真实 TF-IDF 索引而非嵌入模型的理由相同：一个真实的、可测试的内核，未来基于 ML 的分类器可以在识别出的语音需要覆盖超出这个 v0 词汇表的内容时，在同一个 `parse_intent()` 契约背后替换它。
* **为何不匹配的音频/文本会返回一个诚实的未命中，而非一个猜测。** `detect_voice_segments()` 对静音返回空列表，`parse_intent()` 对规则集之外的文本返回 `None`——v0 没有可回退的模型，因此它绝不会捏造一个实际上并未真正检测到的语音段或意图。
* **为何 Watch 网关使用 `classify_intent()` 而非旧版 `parse_intent()`。** 对现有调用方而言，`parse_intent()` 仍保持"第一个匹配即胜出"的行为不变，依旧按原样测试；但一段真正同时匹配多个已知命令的真实转录文本（例如同时包含"stop"和"status"）对于一个全部职责就是判断运动命令是否需要确认的网关来说，是一个真实的、与安全相关的歧义——`classify_intent()` 会检查每一条规则，并报告一个真实、明确区分的歧义情形，而不是悄悄地解析为恰好排在最前面的那条规则。
* **为何 `normalize_text()` 在匹配前应用 Unicode NFKC。** 一些语音转文本流水线会输出全角拉丁字母及其他兼容性 Unicode 形式——这些是与普通 ASCII 不同的码点，因此就 `\b...\b` 正则表达式而言并不算"这个词"。NFKC 会先将它们折叠为普通等价形式，这样一条与已知规则语义相同的命令就不会仅仅因为编码方式的不同而被当成诚实的未命中。

---

## 📂 目录结构

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/
│   ├── audio.py               # 真实的 WAV 加载 + 基于能量的语音活动检测
│   ├── intent.py               # 真实的基于规则的意图/实体解析器 + 具备歧义感知能力的 classify_intent()
│   └── main.py                  # 入口点 + 真实的 `analyze-audio`/`parse-intent` 子命令
├── tests/                    # 真实测试：WAV 夹具、VAD、意图规则、端到端 CLI
├── docs/                     # 文档与指令目录
├── images/                   # 媒体与图表
├── scripts/                  # 实用脚本
├── build/                    # 本地构建输出（已被 git 忽略）
├── pyproject.toml            # 包元数据（版本 0.0.5，里程表式递增）
├── bump_version.py           # 里程表式版本递增（由 build.sh/.bat 使用）
├── build.sh / build.bat      # 创建 venv、安装（含 dev 附加依赖）、验证导入、运行测试
└── run.sh / run.bat          # 运行入口点（转发参数，例如 `analyze-audio`）
```

> **注意：** `hardware/` 和 `firmware/` 已被省略——本节点运行在现成的
> CM5 + Hailo-10 M.2 模块上，没有自己的硬件/固件设计。`os/` 和
> `models/` 也已被省略——HydraOS 镜像和共享的 Hailo-10 模型权重存放在
> 父项目 `HYDRA-UMC-COGNITIVE-NODE` 中，本项目作为一项服务接入其中
> （见其 `docker-compose.yml`）。

---

## ⚙️ 构建与运行

需要 Python >= 3.10。

```bash
# Linux / macOS / Git Bash
./build.sh   # 创建 .venv，安装该包（可编辑模式），验证导入
./run.sh     # 运行入口点

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` 会在每次真实构建之前递增版本号（里程表式，见
`bump_version.py`），并运行真实的测试套件（`pytest tests/`）。不带参数的
`run.sh` 的预期输出：

```text
HYDRA-UMC-VOICE-UI v0.0.5
Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free robotic mission control.
```

真实的子命令会分析一个 WAV 文件，或处理已经转录的文本：

```bash
./run.sh analyze-audio recordings/command.wav
./run.sh parse-intent "start mission alpha"

# Windows
run.bat analyze-audio recordings\command.wav
run.bat parse-intent "status of robot 3"
```

### 🩺 故障排查

* **`python: command not found` / 构建在第 1 步失败。** 需要 `PATH` 中存在 Python >= 3.10。在 Windows 上，从 [python.org](https://python.org) 安装，并确保安装过程中勾选了"Add to PATH"；`python3` 是 Linux/macOS 上的常见命令名。
* **`build.sh` 无法激活 venv。** `python3 -m venv .venv` 在不同平台上生成的激活脚本路径不同：Linux/macOS 上是 `.venv/bin/activate`，Windows（从 Git Bash 使用的 Windows Python venv 也是如此）上是 `.venv/Scripts/activate`。`build.sh` 已经检查了这两个路径——如果仍然失败，删除 `.venv/` 并重新运行 `./build.sh` 从头重建。
* **`pip install -e .` 失败。** 通常是 `.venv/` 已过期。删除 `.venv/` 文件夹并重新运行 `./build.sh`/`build.bat` 重新创建它。
* **`import OK` 从未打印。** 意味着 `python -c "import hydra_umc_voice_ui"` 本身失败了——在激活 venv 的情况下重新运行以查看真实的回溯信息。

---

## 🎙️ WATCH 语音网关（v0）

`python -m hydra_umc_voice_ui.main serve` 为已配对的 HYDRA-UMC-WATCH 集成提供有意限制的本地 HTTP 网关：`GET /health` 和 `POST /v1/voice/turn`。网关会验证类型化的 `voice_turn` 负载，使用现有的确定性意图解析器并返回 `assistant_reply`；它不控制机器人硬件。

回环开发可在无令牌的情况下运行。非回环绑定要求 `HYDRA_UMC_VOICE_UI_TOKEN` 以及匹配的 `Authorization: Bearer` 标头。该 API 绝不传输原始音频，且与运动相关的意图始终返回 `requiresConfirmation: true`。

一段真正同时匹配多个已知命令的转录文本会被拒绝，并返回一个真实、明确区分的回复，而不是被悄悄地解析为单一的理解结果：

```json
{"transcript": "stop the status check"}
// -> {"text": "That request matched more than one action (status, stop). Please rephrase it more specifically.", "requiresConfirmation": false, "intent": null}
```

请求协议和部署边界请参阅 [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md)。

## 🚀 路线图
* **第一阶段：** 在 Hailo-10 上部署 VLA 引擎并进行多模态输入处理。
* **第二阶段：** 语义规划器与集群行为模型及长期记忆的集成。
* **第三阶段：** 语音 UI 的低延迟本地执行以及工业噪声消除。
* **第四阶段：** 多语言支持（英语、西班牙语、德语、法语）以及与 Dashboard AI 的完全集成。

---

## 🔗 相关项目

本项目是同一作者（JuanenRac / Electro Hobby 3D）打造的更大规模机器人生态
系统的一部分，涵盖固件、控制软件、AI 节点和车队工具。

### 与本服务直接相关

- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** / **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** —— 生态系统中的其他语音控制界面。

### 生态系统的其余部分

**HYDRA-UMC 平台** —— 多机器人微工厂单元
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** —— 主板本身：Raspberry Pi CM5 主机 + 双核 STM32H745 实时协处理器，通过 CAN-OTA/SPI-OTA 协调最多 8 条分布式机械臂。
- **[HYDRA-UMC SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** —— 拥有机器人状态的无头 Express/WebSocket 后端。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** —— HYDRA-UMC 的 Android 控制应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** —— HYDRA-UMC 的 iOS/iPadOS 控制应用。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** —— 桌面端集群指挥中心。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** —— 桌面端图形化 URDF 创建/编辑器。

**URTC 平台** —— 每台 HYDRA-UMC 机械臂搭载的工具头控制器
- **[URTC](https://github.com/JuanenRac/URTC)** —— Universal Robot Tool Controller，固件。
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** —— 桌面端 CAN-OTA + SWD/JTAG 刷写工具。
- **[URTC Tester](https://github.com/JuanenRac/URTC-TESTER)** —— 桌面端实时 CAN 总线诊断工具。
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** —— 上述两款桌面工具的浏览器端替代方案。

**👁️ 视觉 AI 节点（Hailo-8）**
- [HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)
- [HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)
- [HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)
- [HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)
- [HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)

**🐝 编排与集群**
- [HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)
- [HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)
- [HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)
- [HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)
- [HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)

**🎮 数字孪生与仿真**
- [HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)
- [HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)
- [HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)
- [HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)

**📊 数据与分析**
- [HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)
- [HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)
- [HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)
- [HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)

**🏭 工业网关**
- [HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)
- [HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)
- [HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)
- [HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)

**🛠️ 配套工具**
- [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)
- [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)
- [HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)
- [HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)
- [HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)

---

## 👤 作者
**JuanenRac**（Electro Hobby 3D）
📧 electrohobby3d@gmail.com

## 📜 许可证
GPL-3.0 —— 详见 LICENSE。
