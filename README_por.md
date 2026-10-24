<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-VOICE-UI banner" width="100%">
</p>

# 🎙️ HYDRA-UMC-VOICE-UI

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | 🇵🇹 <b>Português</b></p>

### 🔊 Pipeline local de voz para ação, acelerado por hardware

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/STT-Whisper%20Local-FF6F00.svg" alt="STT">
  <img src="https://img.shields.io/badge/Platform-Hailo--10-green.svg" alt="Hailo-10">
</p>

**Verificação de honestidade - o que realmente funciona hoje:** o carregamento de WAV e a deteção de atividade de voz por limiar de energia (`audio.py`), o analisador de intenções/entidades baseado em regras e o seu `classify_intent()` sensível a ambiguidades (`intent.py`), o gateway de texto para intenção, limitado e condicionado por confirmação, com uma janela de validade de confirmação real e limitada (`gateway.py` - um `confirmationToken` autodescritivo, assinado com HMAC e de utilização única, nomeia a intenção/entidades exatas para que foi emitido, pelo que uma confirmação tardia/repetida nunca pode autorizar uma ação entretanto desatualizada, nem para lá da sua própria expiração real), e a fronteira HTTP autenticada para o relé do Watch, incluindo o `POST /v1/voice/confirm` (`http_service.py`) são reais e testados - 169 testes a passar (`pytest tests/`), incluindo uma suíte real de ponta a ponta contra um `VoiceGatewayServer` em direto (token exigido/aceite/recusado, uma ida e volta real de `POST /v1/voice/turn`/`POST /v1/voice/confirm`, corpos malformados/demasiado grandes, um `Content-Length` genuinamente em falta). Nada disto precisa de um microfone, de um modelo Whisper nem de um NPU Hailo-10 para ser executado ou testado - `analyze-audio`/`parse-intent`/`serve` funcionam todos hoje sobre um ficheiro WAV ou texto já transcrito. O novo `Dockerfile` reutiliza as mesmas flags da CLI já verificadas em direto na unidade systemd da CM5 real, mas não foi ele próprio testado numa compilação - não há runtime Docker nesta máquina de desenvolvimento. O pipeline real de STT Whisper e TTS neuronal que o roteiro deste README descreve continua a ser pura aspiração: não foi integrado nenhum modelo de reconhecimento nem de síntese de fala, e este ambiente não tem nenhum módulo Hailo-10 físico onde correr um. Consulte o `CHANGELOG.md` para saber exatamente o que já foi entregue e a própria lista de funcionalidades da secção 1 abaixo para a distinção real/futuro de cada uma.

---

> **Estado de segurança (safety e security):** este ecossistema não é um sistema de segurança certificado. Ainda não existe um caminho de E-STOP por hardware, nem limites ou interlocks impostos pelo firmware, nem um comando de movimento verificado; as imagens de firmware são verificadas com CRC32 e um HMAC-SHA256 de chave partilhada, não com uma assinatura assimétrica; TLS e TLS mútuo são opcionais e estão desativados por defeito; nenhuma placa própria foi ainda montada ou testada. Leia a [base de segurança](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) e o [modelo de ameaças](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de confiar em qualquer afirmação aqui para a segurança de uma pessoa.

## 📋 Num relance

| | |
|---|---|
| Versão | `0.1.8` |
| Maturidade | Funcional |
| Testes | 85 (`pytest tests/`) |
| Tecnologia | Python / Rule-based intent parser / Energy-gate VAD |
| Destino | O Raspberry Pi CM5 de uma célula HYDRA-UMC |
| Em hardware real | Ainda não: não há registo de execução em hardware real para esta versão |

## 🚦 Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje. É escrita com o que o repositório consegue demonstrar (testes, compilações, execuções), não com o que está previsto.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito a meio ou ainda por verificar · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Software | 🟡 | Funciona para o seu propósito principal; a verificação de honestidade acima lista o que ainda falta |
| Testes | 🟢 | 85 testes automáticos, executados a cada alteração |
| Hardware real | 🔴 | Ainda não: não há registo de execução em hardware real para esta versão |
| Documentação | 🟢 | README em oito idiomas, verificado contra o manifesto a cada alteração |

## 1. 🛠️ VISÃO TÉCNICA GERAL

O **HYDRA-UMC-VOICE-UI** é a camada local de interação por voz do ecossistema HYDRA-UMC. Fornece um pipeline de alto desempenho de STT (Speech-to-Text) e TTS (Text-to-Speech) acelerado pelo NPU Hailo-10.

Permite aos operadores controlar missões robóticas, consultar o estado do sistema e receber retorno áudio sem qualquer ligação à nuvem, garantindo a máxima privacidade e latência zero.

### Funcionalidades principais:
* 🎧 **Front-end de áudio (v0):** carregamento de WAV real, só com a biblioteca padrão, e deteção de atividade de voz por limiar de energia. *(implementado como uma primitiva real de processamento de sinal - não é a própria transcrição; ver COMPILAÇÃO E EXECUÇÃO abaixo)*
* 🎙️ **STT na periferia:** modelos Whisper quantizados para transcrição de fala quase instantânea. *(planeado - precisa de uma dependência real de modelo)*
* 📢 **TTS natural:** síntese de voz de alta qualidade para alertas e relatórios de estado do sistema. *(planeado)*
* 🧠 **Analisador NLU (v0):** extração real de intenções/entidades por regras a partir de texto reconhecido, para o Semantic Planner. *(implementado como regras regex sobre um pequeno vocabulário real de comandos - não é um modelo de ML treinado; ver COMPILAÇÃO E EXECUÇÃO abaixo)*
* 🔀 **Classificação sensível a ambiguidades:** o `classify_intent()` normaliza o texto (Unicode NFKC, remoção de enchimento/pontuação) e rejeita uma transcrição que corresponda genuinamente a mais de um comando conhecido, em vez de adivinhar um em silêncio. *(implementado; usado pelo gateway de voz do Watch abaixo)*
* 🔏 **Confirmações assinadas e de utilização única (v0):** o `confirmationToken` que confirma uma paragem, o início de uma missão ou o regresso a casa é assinado com HMAC-SHA256 sob uma chave do servidor (`HYDRA_UMC_VOICE_UI_CONFIRM_SECRET`, com pelo menos 16 caracteres; sem ela cria-se uma chave aleatória por processo), leva um nonce aleatório e é aceite uma única vez: uma segunda utilização do mesmo token, um token de outra intenção montado à mão ou um assinado com outra chave é recusado como `invalid`. Antes, o token era um prefixo SHA-256 do seu próprio conteúdo sem segredo, pelo que qualquer pessoa que conhecesse o formato podia construir uma confirmação válida, e uma válida podia ser repetida durante os seus 30 segundos. O instalador do OS gera a chave com os restantes segredos do dispositivo. *(implementado)*
* 🛑 **Uma paragem por voz nunca é retida (definição do servidor):** por omissão um pedido de paragem é respondido de imediato, sem token de confirmação e com `priority: safety-stop` para que um consumidor o converta numa paragem controlada (nunca substitui a paragem de emergência física); iniciar um movimento continua a ser confirmado. `HYDRA_UMC_VOICE_UI_STOP_REQUIRES_CONFIRMATION=1` repõe a confirmação da paragem. *(implementado)*
* 🔏 **Uma confirmação vale para quem a pediu, e um resultado confirmado pode ser verificado:** um turno pode indicar o seu `subject` (o utilizador com sessão iniciada para quem o HYDRA-UMC-SERVER o retransmite); o token de confirmação assinado transporta-o e só confirma para esse mesmo sujeito (uma recusa não consome o token). Um resultado confirmado leva também `subject`, `confirmedAtUtc` e o `nonce` de utilização única e, se `HYDRA_UMC_VOICE_UI_RESULT_KEY` (16 caracteres ou mais, o mesmo valor que o HYDRA-UMC-SERVER tem) estiver definida, uma `signature` HMAC-SHA256 que o servidor verifica antes de acreditar no resultado. `HYDRA_UMC_VOICE_UI_REQUIRE_SUBJECT=1` recusa ainda um turno ou uma confirmação que não nomeie ninguém (desativado por omissão). *(implementado)*
* 🛡️ **Cancelamento de ruído:** otimizado para ambientes industriais com muito ruído ambiente. *(planeado)*
* 👨‍👩‍👧 **Filho do Cognitive AI Node:** corre como um de quatro serviços irmãos
  sob o [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)
  (ao lado do VLA-Engine, Semantic-Planner e Docs-QA), partilhando a imagem
  HydraOS e os pesos de modelo do pai em vez de manter cópias próprias.
* 📦 **Versionamento em odómetro:** A versão do `pyproject.toml` só é subida pelo comando `bump` explícito (`python tools/hydra_project_tool.py bump`, que executa o `bump_version.py`) - compilar nunca a altera.

---

## 2. 🔄 FLUXO DO PIPELINE DE VOZ

```mermaid
flowchart LR
    MIC["Microphone Input"] --> STT["Whisper STT (Hailo-10)"]
    STT --> NLU["Semantic Intent Parser"]
    NLU --> LOGIC["Cognitive Node Logic"]
    LOGIC --> TTS["TTS Engine"]
    TTS --> SPK["Speaker Output"]
```

---

## 3. 🧱 ARQUITETURA E DECISÕES DE DESIGN

Este repositório é um **filho** da família Cognitive AI Node - o seu pai, o [HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE), é dono da imagem HydraOS partilhada e dos pesos de modelo quantizados, e liga este serviço ao `docker-compose.yml` ao lado dos seus três irmãos (VLA-Engine, Semantic-Planner, Docs-QA):

* **Porque é que este filho não tem hardware/firmware/`os/`/`models/` próprios.** Corre inteiramente na CM5 + módulo M.2 Hailo-10 que o pai já possui - manter os pesos dos modelos e a imagem HydraOS centralizados num só sítio evita quatro cópias divergentes de vários gigabytes em toda a família.
* **Porque é que há um layout `src/`.** Mantém o pacote instalável (`hydra_umc_voice_ui`) separado das ferramentas da raiz do repositório (`bump_version.py`), em linha com o layout usado por todos os outros projetos Python do ecossistema.
* **Porque é que a invocação sem argumentos só imprime identidade/versão/papel.** Isso continua a ser uma verificação de esqueleto fina e inalterada; o trabalho real da v0 vive atrás dos seus subcomandos - `analyze-audio` (carregamento real de WAV + VAD por limiar de energia, `audio.py`), `parse-intent` (análise real de intenções/entidades por regras, `intent.py`) e `serve` (o gateway real e autenticado de turnos de voz do Watch, `http_service.py`/`gateway.py`). Nada disso é o pipeline de STT Whisper / TTS neuronal que o roteiro deste README descreve - esse ainda precisa de uma dependência real de modelo que este ambiente não tem.
* **Como isto se encaixa no resto do ecossistema.** Este serviço é o ponto de entrada mãos-livres de todo o Cognitive AI Node: a intenção reconhecida flui para o seu irmão HYDRA-UMC-SEMANTIC-PLANNER, e atua como superfície de controlo por voz ao lado do HYDRA-UMC-STUDIO e do HYDRA-UMC-DSI.
* **Porque é que o `audio.py` usa `wave`/`array` em vez de numpy.** A descodificação de PCM de 16 bits e um VAD real por limiar de energia não precisam de nada além do que a biblioteca padrão já oferece - manter a v0 sem dependências significa que o front-end de áudio real funciona onde quer que o Python funcione, antes mesmo de qualquer dependência de STT específica do Hailo-10 estar instalada.
* **Porque é que o `intent.py` são regras regex reais e não um modelo NLU treinado.** Um pequeno vocabulário real de comandos (iniciar/parar/estado/ir para casa) está total e honestamente coberto por regras hoje - o mesmo raciocínio do índice TF-IDF real do irmão HYDRA-UMC-DOCS-QA em vez de um modelo de embeddings: um núcleo real e testável agora, que um futuro classificador baseado em ML pode substituir por trás do mesmo contrato `parse_intent()`, quando a fala reconhecida precisar de cobrir mais do que este vocabulário da v0.
* **Porque é que o áudio/texto sem correspondência devolve uma falha honesta e não um palpite.** O `detect_voice_segments()` devolve uma lista vazia para o silêncio, e o `parse_intent()` devolve `None` para texto fora do seu conjunto de regras - a v0 não tem nenhum modelo a que recorrer, pelo que nunca fabrica um segmento ou uma intenção que não detetou realmente.
* **Porque é que o gateway do Watch usa o `classify_intent()` e não o `parse_intent()` legado.** O `parse_intent()` continua a ser de primeira correspondência ganha (inalterado, ainda testado tal como está) para os chamadores existentes, mas uma transcrição real que corresponda genuinamente a mais de um comando conhecido (por exemplo, contendo «stop» e «status») é uma ambiguidade real e relevante para a segurança num gateway cuja função inteira é decidir se um comando de movimento precisa de confirmação - o `classify_intent()` verifica todas as regras e reporta um caso ambíguo real e distinto, em vez de resolver em silêncio para qualquer regra que esteja declarada primeiro.
* **Porque é que o `normalize_text()` aplica Unicode NFKC antes de comparar.** Alguns pipelines de reconhecimento de fala emitem letras latinas de largura total e outras formas Unicode de compatibilidade - pontos de código distintos do ASCII normal e, portanto, não «a palavra» no que toca a uma regex `\b...\b`. O NFKC reduz-os primeiro ao seu equivalente normal, para que um comando semanticamente idêntico a uma regra conhecida nunca seja tratado como uma falha honesta só por causa da forma como foi codificado.

---

## 📂 ESTRUTURA DE DIRETORIAS

```text
HYDRA-UMC-VOICE-UI/
├── src/hydra_umc_voice_ui/
│   ├── __init__.py            # Descrição e versão do pacote
│   ├── audio.py               # Carregamento real de WAV + deteção de atividade de voz por limiar de energia
│   ├── intent.py               # Analisador real de intenções/entidades por regras + classify_intent() sensível a ambiguidades
│   ├── gateway.py               # Gateway limitado de texto para intenção partilhado pelo fluxo cognitivo do Watch
│   ├── http_service.py          # Pequena fronteira HTTP da biblioteca padrão para o caminho de voz do Watch ao nó cognitivo
│   ├── main.py                  # Ponto de entrada + subcomandos reais `analyze-audio`/`parse-intent`
│   └── ratelimit.py             # Um limite de pedidos por endereço de cliente em janela deslizante (para que um cliente não encha a lista de confirmações)
├── tests/                    # Testes reais: fixtures WAV, VAD, regras de intenção, gateway, CLI de ponta a ponta
├── docs/                     # Documentação e catálogo de comandos
├── images/                   # Multimédia e diagramas
├── deploy/
│   └── voice-ui.env.example  # Modelo de ambiente do gateway local da CM5
├── systemd/
│   └── hydra-umc-voice-ui.service # Unidade systemd do serviço HTTP de voz local da CM5
├── tools/
│   ├── build_test.py         # Verificação de compilação sem alterar versões
│   ├── ci_validate.py        # Validação de manifesto/CHANGELOG/docs usada pelo CI
│   ├── _doc_policy.py        # Regras de documentação partilhadas pela família (cópia da de HYDRA-UMC-SDK, mantida em sincronia)
│   ├── _readme_parity.py     # Verificação de que os oito README partilham a mesma estrutura (cópia da de HYDRA-UMC-SDK, mantida em sincronia)
│   └── hydra_project_tool.py # Os mesmos comandos em todos os repositórios: validate, test, ci, version, status, bump
├── build/                    # Saída de compilação local (ignorada pelo git)
├── Dockerfile                # Imagem de contentor mínima para o gateway HTTP autenticado (não root)
├── pyproject.toml            # Metadados do pacote (versão subida só pelo comando bump explícito)
├── bump_version.py           # Subida de versão ao estilo conta-quilómetros (executada só pelo comando `bump` explícito)
├── bump_manifest_version.py  # Sincroniza a versão do hydra-umc.project.json com a nativa (--sync)
├── build.sh / build.bat      # Cria o venv, instala (com extras de desenvolvimento), verifica a importação e executa os testes
├── build-test.sh / build-test.bat # Envólucro sem alterações de tools/build_test.py (sem mudar versão/manifesto/CHANGELOG)
└── run.sh / run.bat          # Executa o ponto de entrada (reencaminha argumentos, p. ex. `analyze-audio`)
```

> **Nota:** `hardware/` e `firmware/` foram retirados - este nó corre numa CM5 + módulo M.2 Hailo-10 já existentes, sem desenho de hardware/firmware próprio. `os/` e `models/` também foram retirados - a imagem HydraOS e os pesos de modelo Hailo-10 partilhados vivem no pai `HYDRA-UMC-COGNITIVE-NODE`, a que este projeto se liga como serviço (ver o seu `docker-compose.yml`).

---

## ⚙️ GUIA DE COMPILAÇÃO E EXECUÇÃO

Requer Python >= 3.10.

```bash
# Linux / macOS / Git Bash
./build.sh   # cria o .venv, instala o pacote (editável), verifica a importação
./run.sh     # executa o ponto de entrada

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` nunca alteram a versão (só `python tools/hydra_project_tool.py bump` a sobe) e executam a suíte de testes real (`pytest tests/`). Saída esperada de um `run.sh` sem argumentos:

```text
HYDRA-UMC-VOICE-UI v0.1.8
Voice UI (Hailo-10) - local STT/TTS pipeline for hands-free robotic mission control.
```

Os subcomandos reais analisam um ficheiro WAV ou interpretam texto já transcrito:

```bash
./run.sh analyze-audio recordings/command.wav
./run.sh parse-intent "start mission alpha"

# Windows
run.bat analyze-audio recordings\command.wav
run.bat parse-intent "status of robot 3"
```

### 🩺 Resolução de problemas

* **`python: command not found` / a compilação falha no passo 1.** Requer Python >= 3.10 no `PATH`. No Windows, instale a partir de [python.org](https://python.org) e confirme que «Add to PATH» ficou marcado durante a instalação; `python3` é o nome habitual em Linux/macOS.
* **O `build.sh` não consegue ativar o venv.** O `python3 -m venv .venv` coloca o script de ativação de forma diferente por plataforma: `.venv/bin/activate` em Linux/macOS, `.venv/Scripts/activate` no Windows (também verdade para um venv de Python do Windows usado a partir do Git Bash). O `build.sh` já verifica ambos os caminhos - se ainda assim falhar, apague o `.venv/` e volte a executar `./build.sh` para o reconstruir de raiz.
* **O `pip install -e .` falha.** Normalmente é um `.venv/` obsoleto. Apague a pasta `.venv/` e volte a executar `./build.sh`/`build.bat` para a recriar.
* **O `import OK` nunca aparece.** Significa que o próprio `python -c "import hydra_umc_voice_ui"` falhou - volte a executar com o venv ativo para ver o traceback real.

---

## 🎙️ GATEWAY DE VOZ DO WATCH (v0)

O `python -m hydra_umc_voice_ui.main serve` expõe um gateway HTTP local deliberadamente limitado para uma integração com o HYDRA-UMC-WATCH emparelhado: `GET /health`, `POST /v1/voice/turn` e `POST /v1/voice/confirm`. O gateway valida o payload tipado `voice_turn`, usa o analisador de intenções determinista existente e devolve um `assistant_reply`; não controla hardware de robôs.

O desenvolvimento em loopback pode correr sem token. Um bind que não seja loopback exige `HYDRA_UMC_VOICE_UI_TOKEN` e um cabeçalho `Authorization: Bearer` correspondente. O áudio bruto nunca é enviado por esta API, e as intenções relacionadas com movimento devolvem sempre `requiresConfirmation: true` juntamente com um `confirmationToken` real e limitado - o cliente Watch devolve-o ao `POST /v1/voice/confirm`, que reporta `confirmed`/`expired`/`invalid` (nunca um booleano simples) sem despachar nada por si próprio. Consulte a secção de confirmação do [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) abaixo para o contrato completo.

Uma transcrição que corresponda genuinamente a mais de um comando conhecido é rejeitada com uma resposta real e distinta em vez de ser resolvida em silêncio para uma interpretação:

```json
// POST /v1/voice/turn
{"type": "voice_turn", "requestId": "watch-voice-001", "transcript": "stop the status check", "locale": "en-US"}

// -> {"type":"assistant_reply","requestId":"watch-voice-001","text":"That request matched more than one action (status, stop). Please rephrase it more specifically.","level":"ATTENTION","speak":true,"requiresConfirmation":false,"visualState":"clarification","interpretation":{"heardText":"stop the status check","normalizedText":"stop the status check","matchedRules":["status","stop"]}}
```

Consulte o [WATCH_VOICE_GATEWAY.md](docs/WATCH_VOICE_GATEWAY.md) para o contrato completo dos pedidos e a fronteira de implantação, e o [CLI_REFERENCE.md](docs/CLI_REFERENCE.md) para cada exemplo real de `analyze-audio`/`parse-intent`/`serve` capturado da CLI instalada.

## 🚀 ROTEIRO
* **Fase 1:** Implantação do motor VLA e processamento de entrada multimodal no Hailo-10.
* **Fase 2:** Integração do planeador semântico com modelos comportamentais do enxame e memória de longo prazo.
* **Fase 3:** Execução local de baixa latência do Voice UI e cancelamento de ruído industrial.
* **Fase 4:** Suporte multilingue (inglês, espanhol, alemão, francês) e integração total com o Dashboard AI.

---

## 🔗 Projetos relacionados

Este projeto faz parte do ecossistema de robótica HYDRA-UMC do mesmo autor (JuanenRac / Electro Hobby 3D). Vale a pena conhecê-los, porque um pedido pode ser, na verdade, sobre um destes e não sobre este repositório.

**Projeto-mãe**
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — centro de integração do pipeline cognitivo do Hailo-10 (orquestração de LLM/VLA/voz); o pai de que este repositório é uma etapa ou consumidor específico, dentro do seu próprio pipeline cognitivo.

**Projetos irmãos** — as outras etapas/consumidores do próprio pipeline cognitivo Hailo-10 do HYDRA-UMC-COGNITIVE-NODE
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — decomposição real de tarefas baseada em regras e recuperação semântica de erros sobre os códigos de erro do MCU.
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — codificação/descodificação real de tokens de ação e geração de trajetórias para um modelo Visão-Linguagem-Ação.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — pesquisa real de documentos TF-IDF só com a biblioteca padrão sobre a documentação Markdown deste ecossistema.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — técnico de manutenção de IA local, protegido por políticas, para o próprio ecossistema: observa, diagnostica e propõe correções; os dois níveis de maior risco não estão implementados de propósito.

**Diretamente relacionados**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — painel web de controlo com visualização 3D em tempo real de vários robôs; outra superfície de controlo por voz do ecossistema, ao lado deste serviço.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tátil nativa para o ecrã tátil DSI de 7" integrado, executada no próprio CM5; outra superfície de controlo por voz do ecossistema, ao lado deste serviço.

**Também fazem parte do ecossistema**

*Hardware e plataforma centrais*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — o desenho da placa-mãe do braço robótico: anfitrião CM5 + STM32H745 de dois núcleos, pensado para orquestrar até 8 braços de ferramenta por CAN-OTA/SPI-OTA (firmware numa fase inicial; ainda sem placa montada).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — camada de produto reproduzível do Raspberry Pi OS para o CM5: agente só de leitura, configuração/perfis validados, aprovisionamento Wi-Fi de primeiro contacto.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — o contrato JSON-Schema partilhado e a fronteira de software de controlo de trabalhos contra a qual cada bridge valida os seus comandos (não é uma função de segurança certificada).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registo declarativo de manifestos de adaptador e validador para conectores de máquinas externas; estende a ideia de contrato do SDK a máquinas externas sem substituir os projetos de gateway industrial.

*Backend central e clientes*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — o back-end headless real (REST/WebSocket) com que todos os clientes de controlo realmente comunicam.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centro de comando de enxame para desktop (PySide6) para vários servidores ao mesmo tempo, empacotado como executável independente.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — aplicação Android nativa de controlo, com início de sessão biométrico e um companheiro Wear OS emparelhado.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — aplicação de controlo para iOS/iPadOS (Flutter) com sincronização WebSocket em tempo real.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — criador/editor gráfico de URDF para desktop que envia os modelos concluídos para o catálogo do STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — editor de modelos STL para desktop que transforma/substitui/remove/adiciona peças reais no mesmo catálogo de modelos que o HYDRA-UMC-EDITOR-URDF também edita.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — fronteira de coordenação para frotas AGV/AMR através de um publicador MQTT VDA 5050 (testado apenas contra uma frota emulada).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordenador de células CNC de alto nível com acesso ao estado GRBL e aos bytes de controlo (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — fronteira de coordenação para droides com patas/humanoides, com um emissor de comandos para o Boston Dynamics Spot (testado apenas contra um emulador).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordenador de células laser que lê 3 sinais GPIO (chave, caixa e interlock) (testado apenas contra um chip simulado; não pode armar nem disparar um laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordenador seguro de fluxo de placa de alto nível para pick-and-place com OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — fronteira de coordenação segura para impressoras 3D Moonraker/Klipper, com comandos de trabalho reais protegidos por portas.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordenador com um transporte ROS 2 baseado em rclpy importado sob demanda (ainda não executado contra uma instalação ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — fronteira de coordenação para UAV com câmara, com um emissor de comandos MAVLink (testado apenas contra um emulador).

*Plataforma de ferramentas URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware da placa física Universal Robot Tool Controller, mais de 25 perfis de ferramenta por barramento CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — ferramenta gráfica de gravação para desktop das placas URTC, por CAN-OTA e também SWD/JTAG de chip completo.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — ferramenta de diagnóstico CAN em tempo real para desktop das placas URTC, com um painel por perfil de ferramenta.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternativa no navegador ao URTC-TESTER através da Web Serial API, sem instalação local.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway à frente do barramento CAN do URTC: lista de identificadores permitidos, limite de taxa e chave de sessão; software testado num computador, ainda não num barramento real.

*Nó de IA de visão (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — centro de integração do pipeline de visão Hailo-8, com uma verificação real de prontidão de hardware por fase.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registo real de modelos compilados com verificação segura de carga por arquitetura Hailo e soma de verificação.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — pipeline GStreamer real e gerador de configuração MediaMTX com uma fronteira de integração HailoRT real.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — lei de correção de servovisão baseada em posição com autorização condicionada ao estado da zona; ainda sem estimativa de pose por câmara.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — lógica v0 de violação de zonas, atualidade da calibração e pedido de E-STOP que lê as posições dos objetos de um ficheiro; nenhum detetor a alimenta e ainda não há E-STOP físico ligado.

*Orquestração e enxame*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — centro de integração com um contrato real de relatório de saúde gRPC/Protobuf e uma máquina de estados de missões.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — fila real de trabalhos por prioridade com deduplicação, sobre uma API HTTP real.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vigilante real de saúde da frota por gRPC com repetição/recuo e deteção de identidade incoerente.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — planeador real de trajetórias 3D baseado em RRT com validação real de colisões com obstáculos e espaço de trabalho.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — sincronização real de estado CRDT LWW-Element-Map, testada por propriedades para a convergência de várias células.

*Gémeo digital e simulação*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — centro de integração do motor de gémeo digital, com um contrato real de sincronização de compatibilidade de versões.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — encaminhador hardware-in-the-loop com um interlock de software de colisão entre a simulação e o hardware real (testado sem hardware real).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — cinemática direta real e validação de limites de juntas sobre um subconjunto real de URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — gerador procedural real de cenas 2D com exportação de anotações YOLO/COCO.

*Dados e análise*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — armazém real de séries temporais sobre sqlite3 com uma API HTTP real de ingestão/consulta.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — detetor real de anomalias por FFT e linha de base estatística, com monitorização de deriva.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — cálculo real de OEE/disponibilidade sobre o histórico do DATALAKE, com exportação CSV reprodutível.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — pipeline real de ingestão CAN/WebSocket para o DATALAKE, com deduplicação por sequência.

*Gateway industrial*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — centro de integração que retransmite para protocolos industriais, com uma camada real de lista de comandos permitidos e contrapressão.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — espaço de endereços OPC-UA real, verificado com uma sessão de cliente real do protocolo binário.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — broker MQTT real com autenticação opcional por cliente e ACL de tópicos.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — endpoints XML MTConnect `/probe` e `/current` reais com saída em modo degradado.

*Ferramentas complementares e operações do ecossistema*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — painéis de Resumos Inteligentes e Realce de Anomalias sobre o DATALAKE/ANOMALY-DETECTOR, com um recurso estatístico honesto.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI da frota com um contrato de códigos de saída real e estável, um cliente vivo genuíno da API do HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — aplicação companheira WearOS com padrões de alerta tátil e um relé de voz para o telemóvel emparelhado (ainda não executada num relógio físico).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware de um rack de montagem de placas com descodificação real do ID da ferramenta e lógica de pré-aquecimento Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware mais um companheiro de visão em Python real para uma cabeça de ferramenta de inspeção térmica/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — ferramenta administrativa de desktop que descobre, clona e atualiza todos os repositórios deste ecossistema.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — ferramenta de desktop para Windows/Linux que constrói uma imagem do CM5 pronta a gravar com as versões mais recentes do ecossistema, com configuração de primeiro arranque de Wi-Fi/utilizador/SSH ao estilo do Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordenador de incidentes de manutenção: um papel de borda de poucos privilégios recolhe um inventário/estado higienizado, um papel de plano de controlo mostra-o só de leitura e pede a um fornecedor de IA que sugira um diagnóstico; nunca aplica um patch nem implanta nada.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — anfitrião de desenvolvimento reproduzível (Raspberry Pi 5 / CM5) que guarda o código-fonte do ecossistema e executa tarefas limitadas de compilação/teste numa fila durável; um papel de desenvolvimento dedicado, explicitamente não um CM5 operacional.

---

## 📚 Documentação e comunidade

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pilha tecnológica e diretrizes de código para um pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — as normas de comportamento esperadas nesta comunidade.
- **[SECURITY.md](SECURITY.md)** — como comunicar uma vulnerabilidade e as áreas de segurança em que este projeto se concentra.
- **[SUPPORT.md](SUPPORT.md)** — onde fazer perguntas e comunicar erros.
- **[LICENSE.md](LICENSE.md)** — a licença deste projeto.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENÇA
GPL-3.0 - consulte LICENSE para mais detalhes.

