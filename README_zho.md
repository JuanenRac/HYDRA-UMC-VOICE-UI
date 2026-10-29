<!-- =============================================================================
HYDRA-UMC-VOICE-UI - Local speech-to-action front end
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-VOICE-UI banner" width="100%">
</p>

# 🎙️ HYDRA-UMC-VOICE-UI

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | 🇨🇳 <b>简体中文</b> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🔊 本地硬件加速的语音转动作流水线

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/STT-Whisper%20Local-FF6F00.svg" alt="STT">
  <img src="https://img.shields.io/badge/Platform-Hailo--10-green.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Tests-195%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.8-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-functional-0F6CBD.svg" alt="Maturity">
</p>

---

> **安全与安防现状:**本生态系统不是经认证的安全系统。目前尚无硬件 E-STOP 通路,没有由固件强制执行的限位或联锁,也没有经过验证的运动指令;固件映像使用 CRC-32 和 Ed25519 签名校验,发布构建会拒绝已公开的开发密钥(中继之后的工具头和扩展板仍运行 URTC 的引导程序,它们使用共享密钥的 HMAC-SHA256 而不是签名);TLS 与双向 TLS 均为可选项,默认关闭;自制电路板尚未组装或测试。在依赖此处任何说法来保障人身安全之前,请先阅读[安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)和[威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)。

---

## 📋 速览

| | |
|---|---|
| 版本 | `0.1.8` |
| 成熟度 | 可用 |
| 测试 | 195 (`python -m pytest -q tests`) |
| 技术栈 | Python / Rule-based intent parser / Energy-gate VAD |
| 目标 | HYDRA-UMC 工作单元的 Raspberry Pi CM5 |
| 真实硬件 | 尚未：此版本没有在真实硬件上运行的记录 |

**跳转：** [概述](#-概述) · [架构](#-架构) · [快速开始](#-快速开始) · [测试](#-测试) · [仓库结构](#-仓库结构) · [相关项目](#-相关项目)

## 🚦 项目状态

每一行是本仓库的一个部分，灯号表示它今天做到了哪一步。内容依据仓库能够展示的证据（测试、构建、运行），而不是计划。

🟢 已完成并验证 · 🟡 可用，有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不可用

| 领域 | 状态 | 在这里的含义 |
|---|---|---|
| 软件 | 🟡 | 主要用途可用；上面的诚实性检查列出了仍然缺少的内容 |
| 测试 | 🟢 | 195 项自动测试，每次变更都会运行 |
| 真实硬件 | 🔴 | 尚未：此版本没有在真实硬件上运行的记录 |
| 文档 | 🟢 | 八种语言的 README，每次变更都会与清单核对 |

## 🎯 概述

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
* 🔏 **带签名且一次性的确认（v0）：** 用于确认停止、开始任务或返航的 `confirmationToken` 由服务器密钥（`HYDRA_UMC_VOICE_UI_CONFIRM_SECRET`，至少 16 个字符；未设置时每个进程生成一个随机密钥）通过 HMAC-SHA256 签名，带有随机 nonce，且只被接受一次：同一令牌的第二次使用、手工拼出的其他意图的令牌，或用另一把密钥签名的令牌，都会被作为 `invalid` 拒绝。此前令牌只是其自身内容的 SHA-256 前缀、没有任何密钥，所以任何知道格式的人都能构造出有效确认，而有效确认可在 30 秒内被重放。OS 安装程序会与其他设备密钥一起生成该密钥。*（已实现）*
* 🛑 **语音停止指令从不被拖延（服务器设置）：** 默认情况下，停止请求会立即得到答复，不带确认令牌，并带有 `priority: safety-stop`，以便使用方把它转换为受控停止（它永远不能取代物理急停）；开始运动仍需确认。`HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION=1` 可恢复对停止的确认。*(已实现)*
* 🔏 **确认只对提出请求的人有效，已确认的结果可以验证：** 一个回合可以指明它的 `subject`（HYDRA-UMC-SERVER 代为转发时所用的已登录用户）；带签名的确认令牌携带该值，并且只对同一主体确认（被拒绝不会消耗令牌）。已确认的结果还包含 `subject`、`confirmedAtUtc` 和一次性 `nonce`；如果设置了 `HYDRA_UMC_VOICE_UI_RESULT_KEY`（16 个字符或更长，与 HYDRA-UMC-SERVER 持有的值相同），还会带有 HMAC-SHA256 `signature`，服务器先验证它才会相信该结果。`HYDRA_UMC_VOICE_UI_REQUIRE_SUBJECT=1` 还会拒绝不指明任何人的回合或确认（默认关闭）。*（已实现）*
* 🙈 **回复不会重复所说的内容（服务器设置）：** 默认情况下，回复的解释只列出匹配的规则；设置 `HYDRA_UMC_VOICE_UI_INCLUDE_HEARD_TEXT=1` 会加入转写文本（`heardText`、`normalizedText`），它属于个人数据。限制：规则只理解英语，轮次中的 `locale` 会被校验但不会被使用。 服务器也可以通过其 Server Admin 界面为每一轮设置它(以及最低置信度);本服务的环境变量优先于服务器。
* 🛡️ **噪声消除：** 针对高环境噪声的工业环境进行优化。*（计划中）*
* 👨‍👩‍👧 **认知 AI 节点子项目：** 作为
  [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) 下 4 个同级服务之一运行（与 VLA-Engine、Semantic-Planner 和 Docs-QA 并列），共享父项目的 HydraOS 镜像和模型权重，而非各自保留独立副本。

## 🧩 在 HYDRA-UMC 中的角色

**HYDRA-UMC-VOICE-UI** 是认知节点的语音前端：它检测 WAV 文件中的语音，用规则把已识别的文本解析为意图，并为手表流程提供有界的 HTTP 网关，在转交任何内容之前先要求确认。它目前还不识别语音，也从不发送物理指令。

## 🏛️ 架构

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-VOICE-UI architecture" width="100%">
</p>

<details>
<summary>图表的文本版本（Mermaid）</summary>

```mermaid
flowchart LR
    MIC["Microphone Input"] --> STT["Whisper STT (Hailo-10)"]
    STT --> NLU["Semantic Intent Parser"]
    NLU --> LOGIC["Cognitive Node Logic"]
    LOGIC --> TTS["TTS Engine"]
    TTS --> SPK["Speaker Output"]
```

</details>

### 架构与设计决策

本仓库是 Cognitive AI Node 系列的**子项目**——其父项目
[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE) 拥有共享的 HydraOS 镜像和量化模型权重，并将本服务与其另外 3 个同级项目（VLA-Engine、Semantic-Planner、Docs-QA）一同接入 `docker-compose.yml`：

* **为何本子项目没有自己的硬件/固件/`os/`/`models/`。** 它完全运行在父项目已拥有的 CM5 + Hailo-10 M.2 模块上——将模型权重和 HydraOS 镜像集中保存在一处，可避免整个项目族中出现四份互不一致的、动辄数 GB 的副本。
* **为何采用 `src/` 布局。** 使可安装的包（`hydra_umc_voice_ui`）与仓库根目录的工具（`bump_version.py`）分离，与生态系统中其他每个 Python 项目所使用的布局保持一致。
* **为何裸调用今天仍然只打印身份/版本/角色。** 这仍然只是一个轻量、未变的脚手架检查；真正的 v0 工作都在它的子命令背后：`analyze-audio`（真实的 WAV 加载 + 基于能量阈值的语音活动检测，`audio.py`）、`parse-intent`（真实的基于规则的意图/实体解析，`intent.py`），以及 `serve`（面向 Watch 的真实、经过认证的语音轮次网关，`http_service.py`/`gateway.py`）。这些都还不是本 README 自己路线图中描述的 Whisper STT / 神经网络 TTS 流水线——那仍然需要一个这个环境里没有的真实模型依赖。
* **这如何融入生态系统的其余部分。** 本服务是进入整个 Cognitive AI Node 的免提入口点：识别出的意图流向其同级项目 HYDRA-UMC-SEMANTIC-PLANNER，并与 HYDRA-UMC-STUDIO 和 HYDRA-UMC-DSI 一同充当语音控制界面。
* **为何 `audio.py` 使用 `wave`/`array` 而非 numpy。** 16 位 PCM 解码和真实的能量阈值 VAD 除了标准库已经提供的之外，不需要任何东西——让 v0 保持零依赖，意味着真实的音频前端可以在任何运行 Python 的地方工作，甚至在安装任何 Hailo-10 专用 STT 依赖之前就能运行。
* **为何 `intent.py` 是真实的正则规则，而非经过训练的 NLU 模型。** 一个小型真实的命令词汇表（start/stop/status/go home）如今已被规则完全且诚实地覆盖——这与兄弟项目 HYDRA-UMC-DOCS-QA 使用真实 TF-IDF 索引而非嵌入模型的理由相同：一个真实的、可测试的内核，未来基于 ML 的分类器可以在识别出的语音需要覆盖超出这个 v0 词汇表的内容时，在同一个 `parse_intent()` 契约背后替换它。
* **为何不匹配的音频/文本会返回一个诚实的未命中，而非一个猜测。** `detect_voice_segments()` 对静音返回空列表，`parse_intent()` 对规则集之外的文本返回 `None`——v0 没有可回退的模型，因此它绝不会捏造一个实际上并未真正检测到的语音段或意图。
* **为何 Watch 网关使用 `classify_intent()` 而非旧版 `parse_intent()`。** 对现有调用方而言，`parse_intent()` 仍保持"第一个匹配即胜出"的行为不变，依旧按原样测试；但一段真正同时匹配多个已知命令的真实转录文本（例如同时包含"stop"和"status"）对于一个全部职责就是判断运动命令是否需要确认的网关来说，是一个真实的、与安全相关的歧义——`classify_intent()` 会检查每一条规则，并报告一个真实、明确区分的歧义情形，而不是悄悄地解析为恰好排在最前面的那条规则。
* **为何 `normalize_text()` 在匹配前应用 Unicode NFKC。** 一些语音转文本流水线会输出全角拉丁字母及其他兼容性 Unicode 形式——这些是与普通 ASCII 不同的码点，因此就 `\b...\b` 正则表达式而言并不算"这个词"。NFKC 会先将它们折叠为普通等价形式，这样一条与已知规则语义相同的命令就不会仅仅因为编码方式的不同而被当成诚实的未命中。

### WATCH 语音网关（v0）

`python -m hydra_umc_voice_ui.main serve` 为已配对的 HYDRA-UMC-WATCH 集成提供有意限制的本地 HTTP 网关：`GET /health`、`POST /v1/voice/turn` 和 `POST /v1/voice/confirm`。网关会验证类型化的 `voice_turn` 负载，使用现有的确定性意图解析器并返回 `assistant_reply`；它不控制机器人硬件。

回环开发可在无令牌的情况下运行。非回环绑定要求 `HYDRA_UMC_VOICE_UI_TOKEN` 以及匹配的 `Authorization: Bearer` 标头。该 API 绝不传输原始音频，且与运动相关的意图始终返回 `requiresConfirmation: true`，并附带一个真实且有限定的 `confirmationToken`——Watch 客户端会把它回传给 `POST /v1/voice/confirm`，后者报告 `confirmed`/`expired`/`invalid`（绝不是单纯的布尔值），自身不会派发任何内容。完整契约见下文 [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) 的确认部分。

一段真正同时匹配多个已知命令的转录文本会被拒绝，并返回一个真实、明确区分的回复，而不是被悄悄地解析为单一的理解结果：

```json
// POST /v1/voice/turn
{"type": "voice_turn", "requestId": "watch-voice-001", "transcript": "stop the status check", "locale": "en-US"}

// -> {"type":"assistant_reply","requestId":"watch-voice-001","text":"That request matched more than one action (status, stop). Please rephrase it more specifically.","level":"ATTENTION","speak":true,"requiresConfirmation":false,"visualState":"clarification","interpretation":{"heardText":"stop the status check","normalizedText":"stop the status check","matchedRules":["status","stop"]}}
```

完整的请求协议和部署边界请参阅 [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md)，从已安装CLI真实捕获的每个 `analyze-audio`/`parse-intent`/`serve` 示例请参阅 [CLI_REFERENCE.md](docs/CLI_REFERENCE.md)。

## 🚀 快速开始

需要 Python 3.10 或更高版本。

```bash
./build.sh  # Linux, macOS (build.bat on Windows)
./run.sh analyze-audio clip.wav
./run.sh parse-intent "stop robot one"
./run.sh serve --port 8091
```

## 🧪 测试

运行 `python -m pytest -q tests` 会执行 195 个自动测试。 不需要硬件，也不需要这台机器以外的任何东西。

CI 运行 `HYDRA_UMC_CI=1 python tools/ci_validate.py`，检查清单、文档、八个 README 和图片。

## 🏗️ 构建与发布

需要 Python >= 3.10。

```bash
# Linux / macOS / Git Bash
./build.sh   # 创建 .venv，安装该包（可编辑模式），验证导入
./run.sh     # 运行入口点

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` 不会更改版本号（只有 `python tools/hydra_project_tool.py bump` 才会提升），并运行真实的测试套件（`pytest tests/`）。不带参数的
`run.sh` 的预期输出：

```text
HYDRA-UMC-VOICE-UI v0.1.8
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

## 📂 仓库结构

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-VOICE-UI" width="100%">
</p>

<details>
<summary>目录树的文本版本</summary>

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/          源代码
│   ├── __init__.py                  包说明与版本
│   ├── audio.py                     真实的 WAV 加载 + 基于能量的语音活动检测
│   ├── intent.py                    真实的基于规则的意图/实体解析器 + 具备歧义感知能力的 classify_intent()
│   ├── gateway.py                   受限的文本到意图网关,由 Watch 认知流程共享
│   ├── http_service.py              面向 Watch→认知语音路径的小型 stdlib HTTP 边界
│   ├── main.py                      入口点 + 真实的 `analyze-audio`/`parse-intent` 子命令
│   └── ratelimit.py                 按客户端地址的滑动窗口请求限制 (防止单个客户端填满确认列表)
├── tests/                           真实测试：WAV 夹具、VAD、意图规则、gateway、端到端 CLI
├── docs/                            文档与指令目录
├── images/                          媒体与图表
├── deploy/
├── systemd/                         服务单元
├── tools/                           项目工具和 CI 检查
├── .github/                         CI 工作流和 Issue 模板
├── Dockerfile                       用于经认证 HTTP 网关的最小容器镜像（非 root）
├── pyproject.toml                   包的元数据
├── bump_version.py                  显式提升版本
├── bump_manifest_version.py         将 hydra-umc.project.json 的版本与原生版本同步(--sync)
├── build.sh / build.bat             创建 venv、安装（含 dev 附加依赖）、验证导入、运行测试
├── build-test.sh / build-test.bat   tools/build_test.py 的非破坏性包装脚本（不改动版本号/manifest/CHANGELOG）
├── run.sh / run.bat                 运行入口点（转发参数，例如 `analyze-audio`）
├── CHANGELOG.md                     每个版本的变更
├── hydra-umc.project.json           清单：版本、成熟度、系列
└── test.sh                          运行测试
```

</details>

## 🗺️ 路线图与已知限制

**当前已知限制**

* **第一阶段：** 在 Hailo-10 上部署 VLA 引擎并进行多模态输入处理。
* **第二阶段：** 语义规划器与集群行为模型及长期记忆的集成。
* **第三阶段：** 语音 UI 的低延迟本地执行以及工业噪声消除。
* **第四阶段：** 多语言支持（英语、西班牙语、德语、法语）以及与 Dashboard AI 的完全集成。

## 🌍 语言

本 README 和仓库文档提供八种语言：英语、西班牙语、德语、法语、意大利语、日语、中文和葡萄牙语（葡萄牙）。它们同时编写，并由 CI 检查八个文件拥有相同的章节和相同的链接。 本仓库没有自己的界面或消息目录，因此没有需要翻译的界面文字。

## 🔗 相关项目

本项目是同一作者(JuanenRac / Electro Hobby 3D)打造的 HYDRA-UMC 机器人生态系统的一部分。值得了解,因为某个请求实际上可能是关于这些项目之一,而非本仓库本身。

**父项目**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — 面向 Hailo-10 认知流水线(LLM/VLA/语音编排)的集成中枢;本仓库是其自身认知流水线中一个具体阶段或消费者所属的父项目。

**兄弟项目** —— HYDRA-UMC-COGNITIVE-NODE 自身 Hailo-10 认知流水线中的其他阶段/消费者
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — 基于真实规则的任务分解，以及针对 MCU 错误码的语义化错误恢复。
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — 面向 Vision-Language-Action 模型的真实动作 token 编解码与轨迹生成。
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — 面向本生态系统自身 Markdown 文档的真实纯标准库 TF-IDF 文档检索。
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — 面向生态系统自身的本地、按策略门控的 AI 维护技师——观察、诊断并提出修复建议;两个最高风险等级目前特意尚未实现。

**直接相关**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — 具有实时多机器人 3D 可视化的网页控制面板;与本服务并列的生态系统另一个语音控制界面。
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — 面向机载 7 英寸 DSI 触摸屏的原生触控界面,直接嵌入 CM5 本体;与本服务并列的生态系统另一个语音控制界面。

**生态系统中的其他项目**

*核心硬件与平台*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — 机器人手臂主板设计——CM5 主机 + 双核 STM32H745,目标是通过 CAN-OTA/SPI-OTA 协调最多 8 条工具臂(固件处于早期阶段,尚无已组装的电路板)。
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — 面向 CM5 的可复现 Raspberry Pi OS 产品层——只读代理、经过验证的配置/配置文件、WiFi 首次配网。
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — 每个桥接都据此校验自身指令的共享 JSON-Schema 契约与软件作业门限边界(并非经认证的安全功能)。
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — 面向外部机器连接器的声明式适配器清单注册与校验工具；把 SDK 自身的契约理念扩展到外部机器，而不取代工业网关类项目。

*核心后端与客户端*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — 每个控制客户端真正通信的真实无头后端(REST/WebSocket)。
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — 面向多台服务器的桌面(PySide6)集群指挥中心，打包为独立可执行文件。
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — 具有生物识别登录和配对 Wear OS 伴侣应用的原生 Android 控制应用。
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — 具有实时 WebSocket 同步的 iOS/iPadOS 控制应用(Flutter)。
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — 将完成的模型推送到 STUDIO 自身目录的桌面版图形化 URDF 创建/编辑工具。
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — 桌面 STL 模型编辑器，在 HYDRA-UMC-EDITOR-URDF 编辑的同一模型目录中变换/替换/移除/添加真实部件。
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — 通过 VDA 5050 MQTT 发布者为 AGV/AMR 车队提供的协调边界(仅针对仿真车队测试)。
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — 具备 GRBL 状态/控制字节访问能力的高层 CNC 单元协调器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — 面向足式/人形机器人的协调边界,带有 Boston Dynamics Spot 指令发送器(仅针对模拟器测试)。
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — 读取 3 路钥匙/外壳/联锁 GPIO 信号的激光单元协调器(仅针对模拟芯片测试;无法使激光器上膛或发射)。
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — 面向 OpenPnP 贴片机板级流程的安全高层协调器。
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — 面向 Moonraker/Klipper 3D 打印机的安全协调边界，具备真实的受控作业指令。
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — 带有惰性导入 rclpy ROS 2 传输层的协调器(尚未在 ROS 2 环境中运行)。
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — 面向搭载摄像头的无人机的协调边界,带有 MAVLink 指令发送器(仅针对模拟器测试)。

*URTC 工具平台*
- **[URTC](https://github.com/JuanenRac/URTC)** — 面向实体 Universal Robot Tool Controller 板卡的固件，通过 CAN 总线支持 25 种以上工具配置。
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — 面向 URTC 板卡的桌面图形烧录工具，支持 CAN-OTA 以及全芯片 SWD/JTAG。
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — 面向 URTC 板卡的桌面实时 CAN 总线诊断工具，每种工具配置对应一个面板。
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — 通过 Web Serial API 实现的浏览器版 URTC-TESTER 替代方案，无需本地安装。
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — URTC CAN 总线前的网关：允许的标识符列表、速率限制和会话密钥；软件已在计算机上测试，尚未在真实总线上测试。

*视觉 AI 节点(Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — 面向 Hailo-8 视觉流水线的集成中枢，具备逐阶段的真实硬件就绪检测。
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — 具备 Hailo 架构/校验和安全加载验证的真实编译模型注册表。
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — 具备真实 HailoRT 集成边界的真实 GStreamer 流水线 + MediaMTX 配置生成器。
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — 以区域状态为授权条件的 Position-Based Visual Servoing 修正律;尚无摄像头位姿估计。
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — 从文件读取物体位置的 v0 区域入侵、校准新鲜度与 E-STOP 请求逻辑;没有检测器为其供数,也尚未连接任何物理 E-STOP。

*编排与集群*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — 具备真实 gRPC/Protobuf 健康报告契约与任务状态机的集成中枢。
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — 基于真实 HTTP API 的真实优先级任务队列，支持去重。
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — 具备重试/退避与身份不匹配检测的真实基于 gRPC 的车队健康看门狗。
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — 具备真实障碍物/工作空间碰撞校验的真实基于 RRT 的三维路径规划器。
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — 经过多单元收敛属性测试的真实 CRDT LWW-Element-Map 状态同步。

*数字孪生与仿真*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — 面向数字孪生引擎的集成中枢，具备真实的版本兼容性同步契约。
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — 在仿真与真实硬件之间带有软件碰撞联锁的硬件在环路由器(未在真实硬件上测试)。
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — 面向真实 URDF 子集的真实正向运动学与关节限位校验。
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — 具备 YOLO/COCO 标注导出功能的真实程序化 2D 场景生成器。

*数据与分析*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — 具备真实数据摄入/查询 HTTP API 的真实 sqlite3 时序数据存储。
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — 具备漂移监测能力的真实 FFT + 统计基线异常检测器。
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — 基于 DATALAKE 历史数据的真实 OEE/可用率计算，支持可复现的 CSV 导出。
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — 面向 DATALAKE 的真实 CAN/WebSocket 数据摄入管道，支持序列去重。

*工业网关*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — 中继至工业协议的集成中枢，具备真实的指令白名单/背压控制层。
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — 经真实二进制协议客户端会话验证的真实 OPC-UA 地址空间。
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — 具备可选按客户端认证与主题 ACL 的真实 MQTT 代理。
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — 具备降级模式输出的真实 MTConnect `/probe` 与 `/current` XML 端点。

*辅助工具与生态系统运维*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — 基于 DATALAKE/ANOMALY-DETECTOR 的智能摘要与异常高亮面板，具备诚实的统计回退机制。
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — 具备真实、稳定退出码契约的车队 CLI，是 HYDRA-UMC-SERVER 自身 API 的真实在线客户端。
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — 带有触觉提醒模式与配对手机语音中继的 WearOS 伴侣应用(尚未在实体手表上运行)。
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — 面向板卡安装机架的固件，具备真实的工具 ID 解码与 Smart Idle 预热逻辑。
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — 面向热成像/RGB 检测工具头的固件及真实 Python 视觉伴侣程序。
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — 发现、克隆并更新本生态系统中每个仓库的管理类桌面工具。
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** —— 构建即刻可烧录、预装生态系统最新版本的 CM5 镜像的 Windows/Linux 桌面工具,具备类似 Raspberry Pi Imager 风格的首次启动 Wi-Fi/用户/SSH 配置。
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — 维护事件协调器：一个低权限的边缘角色采集经过脱敏的库存/健康快照，一个控制面角色以只读方式渲染它，并请求某个 AI 提供方给出诊断建议——从不应用补丁，也从不部署任何内容。
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — 可复现的开发主机（Raspberry Pi 5 / CM5），保存整个生态系统的源代码，并在持久队列下运行有界的构建/测试任务；这是专用的开发角色，明确区别于运行中的 CM5。

## 📚 文档

更多阅读：

* [生态系统的安全基线](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [生态系统的威胁模型](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [本仓库的更新日志](CHANGELOG.md)
* [本仓库的许可证](LICENSE.md)

## 🤝 参与贡献与社区

* 提交 pull request 之前，请运行 `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py`（或 `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`）：它必须输出 `CI_VALIDATION=PASS`。此检查不要运行 `build.sh` 或 `build.bat`；构建不是检查。
* 八个 README 由 HYDRA-UMC-DOCS 中的同一个源生成；请勿手工编辑。修改源文件，再用 `tools/make_readmes.py` 重新生成。
* 不要在 README 中声称尚未运行过的内容：属实时请写“仅模拟”或“尚未在硬件上试过”。
* 请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)、[行为准则](CODE_OF_CONDUCT.md)、[SECURITY.md](SECURITY.md) 和 [SUPPORT.md](SUPPORT.md)。

## 👤 作者

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 许可证

GPL-3.0-or-later - [LICENSE](LICENSE).
