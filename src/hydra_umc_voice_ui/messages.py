# =============================================================================
# HYDRA-UMC-VOICE-UI - src/hydra_umc_voice_ui/messages.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The sentences of a reply, in the eight languages of the ecosystem.

A reply is chosen by a message code; the text is made here in the language of the
`locale` the client sent (the watch sends its own). A locale that is none of the eight
(en, es, de, fr, it, ja, zh, pt; the region is ignored, `zh-TW` is Chinese) gets
English. The code travels with the reply (`messageCode`) so that a client can also
compose the text itself.
"""
from __future__ import annotations

LANGUAGES = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")
DEFAULT_LANGUAGE = "en"

# {name} placeholders are filled with the parameters of the reply.
MESSAGES: dict[str, dict[str, str]] = {
    "negation": {
        "en": "That request contains a negation, so no action was taken. Please say what you want done, without \"not\" or \"never\".",
        "es": "Esa petición contiene una negación, así que no se ha hecho nada. Di lo que quieres que se haga, sin \"no\" ni \"nunca\".",
        "de": "Diese Anfrage enthält eine Verneinung, daher wurde nichts ausgeführt. Sage, was getan werden soll, ohne \"nicht\" oder \"nie\".",
        "fr": "Cette demande contient une négation, donc aucune action n'a été effectuée. Dites ce que vous voulez, sans \"ne pas\" ni \"jamais\".",
        "it": "Questa richiesta contiene una negazione, quindi non è stata eseguita nessuna azione. Di' cosa vuoi fare, senza \"non\" né \"mai\".",
        "ja": "この依頼には否定が含まれているため、何も実行されませんでした。「ない」や「決して」を使わずに、してほしいことを言ってください。",
        "zh": "该请求包含否定词，因此没有执行任何操作。请直接说出要做的事，不要使用“不”或“从不”。",
        "pt": "Este pedido contém uma negação, por isso não foi feita nenhuma ação. Diga o que quer que seja feito, sem \"não\" nem \"nunca\".",
    },
    "no_match": {
        "en": "I did not understand that safely. Ask for status, start a mission, stop, or go home.",
        "es": "No lo he entendido con seguridad. Pide el estado, inicia una misión, para o vuelve a casa.",
        "de": "Das habe ich nicht sicher verstanden. Frage nach dem Status, starte eine Mission, stoppe oder fahre in die Ausgangsposition.",
        "fr": "Je n'ai pas compris cela de façon sûre. Demandez l'état, lancez une mission, arrêtez ou retournez à la position initiale.",
        "it": "Non l'ho capito in modo sicuro. Chiedi lo stato, avvia una missione, ferma o torna alla posizione iniziale.",
        "ja": "安全に理解できませんでした。状態の確認、ミッションの開始、停止、ホームへの復帰のいずれかを指示してください。",
        "zh": "我无法安全地理解这条指令。请查询状态、开始任务、停止或返回原位。",
        "pt": "Não percebi isso com segurança. Peça o estado, inicie uma missão, pare ou volte à posição inicial.",
    },
    "ambiguous": {
        "en": "That request matched more than one action ({names}). Please rephrase it more specifically.",
        "es": "Esa petición coincide con más de una acción ({names}). Reformúlala con más precisión.",
        "de": "Diese Anfrage passt zu mehr als einer Aktion ({names}). Bitte formuliere sie genauer.",
        "fr": "Cette demande correspond à plusieurs actions ({names}). Reformulez-la plus précisément.",
        "it": "Questa richiesta corrisponde a più di un'azione ({names}). Riformulala in modo più specifico.",
        "ja": "この依頼は複数の操作({names})に該当します。もっと具体的に言い直してください。",
        "zh": "该请求匹配多个操作（{names}）。请更具体地重新表述。",
        "pt": "Este pedido corresponde a mais de uma ação ({names}). Reformule-o de forma mais específica.",
    },
    "status": {
        "en": "Status request{target} understood. Live telemetry will be supplied by the authenticated HYDRA-UMC gateway.",
        "es": "Petición de estado{target} entendida. La telemetría en vivo la aportará la pasarela HYDRA-UMC autenticada.",
        "de": "Statusanfrage{target} verstanden. Die Live-Telemetrie liefert das authentifizierte HYDRA-UMC-Gateway.",
        "fr": "Demande d'état{target} comprise. La télémétrie en direct sera fournie par la passerelle HYDRA-UMC authentifiée.",
        "it": "Richiesta di stato{target} compresa. La telemetria in tempo reale sarà fornita dal gateway HYDRA-UMC autenticato.",
        "ja": "状態の問い合わせ{target}を理解しました。リアルタイムのテレメトリは認証済みの HYDRA-UMC ゲートウェイが提供します。",
        "zh": "已理解状态请求{target}。实时遥测将由经过认证的 HYDRA-UMC 网关提供。",
        "pt": "Pedido de estado{target} compreendido. A telemetria em tempo real será fornecida pela gateway HYDRA-UMC autenticada.",
    },
    "status_target": {
        "en": " for robot {robot}",
        "es": " del robot {robot}",
        "de": " für Roboter {robot}",
        "fr": " pour le robot {robot}",
        "it": " per il robot {robot}",
        "ja": "(ロボット {robot})",
        "zh": "（机器人 {robot}）",
        "pt": " do robô {robot}",
    },
    "not_sure": {
        "en": "I am not sure I heard that correctly, so nothing was started. Please say it again.",
        "es": "No estoy seguro de haberlo oído bien, así que no se ha iniciado nada. Repítelo, por favor.",
        "de": "Ich bin nicht sicher, ob ich das richtig gehört habe, daher wurde nichts gestartet. Bitte wiederhole es.",
        "fr": "Je ne suis pas sûr d'avoir bien entendu, donc rien n'a été lancé. Répétez, s'il vous plaît.",
        "it": "Non sono sicuro di aver sentito bene, quindi non è stato avviato nulla. Ripetilo, per favore.",
        "ja": "正しく聞き取れたか確信が持てないため、何も開始していません。もう一度お願いします。",
        "zh": "我不确定是否听清了，因此没有启动任何操作。请再说一遍。",
        "pt": "Não tenho a certeza de ter ouvido bem, por isso não foi iniciado nada. Diga outra vez, por favor.",
    },
    "start_mission": {
        "en": "Start request for {mission} understood. No motion is executed until an authenticated primary control confirms it.",
        "es": "Petición de iniciar {mission} entendida. No se ejecuta ningún movimiento hasta que un control principal autenticado lo confirme.",
        "de": "Startanfrage für {mission} verstanden. Es wird keine Bewegung ausgeführt, bis eine authentifizierte Hauptsteuerung sie bestätigt.",
        "fr": "Demande de démarrage de {mission} comprise. Aucun mouvement n'est exécuté tant qu'une commande principale authentifiée ne l'a pas confirmée.",
        "it": "Richiesta di avvio di {mission} compresa. Nessun movimento viene eseguito finché un controllo principale autenticato non lo conferma.",
        "ja": "{mission} の開始依頼を理解しました。認証済みのメイン制御が確認するまで、動作は実行されません。",
        "zh": "已理解启动 {mission} 的请求。在经过认证的主控制端确认之前，不会执行任何动作。",
        "pt": "Pedido de início de {mission} compreendido. Nenhum movimento é executado até que um controlo principal autenticado o confirme.",
    },
    "default_mission": {
        "en": "the requested mission",
        "es": "la misión pedida",
        "de": "die angeforderte Mission",
        "fr": "la mission demandée",
        "it": "la missione richiesta",
        "ja": "指定されたミッション",
        "zh": "所请求的任务",
        "pt": "a missão pedida",
    },
    "go_home": {
        "en": "Go-home request understood. No motion is executed until an authenticated primary control confirms it.",
        "es": "Petición de volver a casa entendida. No se ejecuta ningún movimiento hasta que un control principal autenticado lo confirme.",
        "de": "Anfrage zur Rückkehr in die Ausgangsposition verstanden. Es wird keine Bewegung ausgeführt, bis eine authentifizierte Hauptsteuerung sie bestätigt.",
        "fr": "Demande de retour à la position initiale comprise. Aucun mouvement n'est exécuté tant qu'une commande principale authentifiée ne l'a pas confirmée.",
        "it": "Richiesta di ritorno alla posizione iniziale compresa. Nessun movimento viene eseguito finché un controllo principale autenticato non lo conferma.",
        "ja": "ホームへの復帰依頼を理解しました。認証済みのメイン制御が確認するまで、動作は実行されません。",
        "zh": "已理解返回原位的请求。在经过认证的主控制端确认之前，不会执行任何动作。",
        "pt": "Pedido de regresso à posição inicial compreendido. Nenhum movimento é executado até que um controlo principal autenticado o confirme.",
    },
    "status_held": {
        "en": "Status request understood. It is held until it is confirmed.",
        "es": "Petición de estado entendida. Queda retenida hasta que se confirme.",
        "de": "Statusanfrage verstanden. Sie wird zurückgehalten, bis sie bestätigt wird.",
        "fr": "Demande d'état comprise. Elle est retenue jusqu'à sa confirmation.",
        "it": "Richiesta di stato compresa. Resta in attesa finché non viene confermata.",
        "ja": "状態の問い合わせを理解しました。確認されるまで保留されます。",
        "zh": "已理解状态请求。在确认之前将保持等待。",
        "pt": "Pedido de estado compreendido. Fica retido até ser confirmado.",
    },
    "stop_now": {
        "en": "Stop request understood and sent without waiting for a confirmation. The physical E-STOP remains the immediate safety action.",
        "es": "Petición de parada entendida y enviada sin esperar confirmación. La parada de emergencia física sigue siendo la acción de seguridad inmediata.",
        "de": "Stoppanfrage verstanden und ohne Bestätigung gesendet. Der physische NOT-AUS bleibt die unmittelbare Sicherheitsmaßnahme.",
        "fr": "Demande d'arrêt comprise et envoyée sans attendre de confirmation. L'arrêt d'urgence physique reste l'action de sécurité immédiate.",
        "it": "Richiesta di arresto compresa e inviata senza attendere conferma. L'arresto di emergenza fisico resta l'azione di sicurezza immediata.",
        "ja": "停止の依頼を理解し、確認を待たずに送信しました。物理的な非常停止が引き続き即時の安全措置です。",
        "zh": "已理解停止请求，并且无需等待确认直接发送。物理急停仍是即时的安全措施。",
        "pt": "Pedido de paragem compreendido e enviado sem esperar confirmação. A paragem de emergência física continua a ser a ação de segurança imediata.",
    },
    "stop_confirm": {
        "en": "Stop request understood. Use the physical E-STOP or authenticated primary control for immediate safety action.",
        "es": "Petición de parada entendida. Usa la parada de emergencia física o el control principal autenticado para una acción de seguridad inmediata.",
        "de": "Stoppanfrage verstanden. Verwende den physischen NOT-AUS oder die authentifizierte Hauptsteuerung für eine sofortige Sicherheitsmaßnahme.",
        "fr": "Demande d'arrêt comprise. Utilisez l'arrêt d'urgence physique ou la commande principale authentifiée pour une action de sécurité immédiate.",
        "it": "Richiesta di arresto compresa. Usa l'arresto di emergenza fisico o il controllo principale autenticato per un'azione di sicurezza immediata.",
        "ja": "停止の依頼を理解しました。即時の安全措置には、物理的な非常停止または認証済みのメイン制御を使用してください。",
        "zh": "已理解停止请求。如需立即采取安全措施，请使用物理急停或经过认证的主控制端。",
        "pt": "Pedido de paragem compreendido. Use a paragem de emergência física ou o controlo principal autenticado para uma ação de segurança imediata.",
    },
    "needs_policy": {
        "en": "The request was recognized but needs an updated safety policy before it can be handled.",
        "es": "La petición se ha reconocido, pero necesita una política de seguridad actualizada antes de poder tramitarse.",
        "de": "Die Anfrage wurde erkannt, benötigt aber eine aktualisierte Sicherheitsrichtlinie, bevor sie bearbeitet werden kann.",
        "fr": "La demande a été reconnue, mais elle nécessite une politique de sécurité à jour avant d'être traitée.",
        "it": "La richiesta è stata riconosciuta, ma richiede una politica di sicurezza aggiornata prima di poter essere gestita.",
        "ja": "依頼は認識されましたが、処理するには安全ポリシーの更新が必要です。",
        "zh": "已识别该请求，但需要更新安全策略后才能处理。",
        "pt": "O pedido foi reconhecido, mas precisa de uma política de segurança atualizada antes de poder ser tratado.",
    },
    "not_activated": {
        "en": "Say the wake word first, or use push-to-talk. Nothing was done.",
        "es": "Di primero la palabra de activación o usa pulsar para hablar. No se ha hecho nada.",
        "de": "Sage zuerst das Aktivierungswort oder nutze Push-to-Talk. Es wurde nichts ausgeführt.",
        "fr": "Dites d'abord le mot d'activation ou utilisez l'appui pour parler. Aucune action n'a été effectuée.",
        "it": "Pronuncia prima la parola di attivazione o usa il push-to-talk. Non è stato fatto nulla.",
        "ja": "先にウェイクワードを言うか、プッシュトゥトークを使ってください。何も実行されていません。",
        "zh": "请先说出唤醒词，或使用按键通话。没有执行任何操作。",
        "pt": "Diga primeiro a palavra de ativação ou use o premir para falar. Não foi feita nenhuma ação.",
    },
    "speaker_not_authorised": {
        "en": "I could not confirm that you are an authorised operator, so the movement was not requested.",
        "es": "No he podido confirmar que eres un operador autorizado, así que no se ha pedido el movimiento.",
        "de": "Ich konnte nicht bestätigen, dass du ein berechtigter Bediener bist, daher wurde die Bewegung nicht angefordert.",
        "fr": "Je n'ai pas pu confirmer que vous êtes un opérateur autorisé, donc le mouvement n'a pas été demandé.",
        "it": "Non ho potuto confermare che sei un operatore autorizzato, quindi il movimento non è stato richiesto.",
        "ja": "許可されたオペレーターであることを確認できなかったため、動作は要求されませんでした。",
        "zh": "无法确认您是授权操作员，因此没有请求该动作。",
        "pt": "Não consegui confirmar que é um operador autorizado, por isso o movimento não foi pedido.",
    },
    "node_query": {
        "en": "The state of {node} is read by the server.",
        "es": "El servidor lee el estado de {node}.",
        "de": "Der Zustand von {node} wird vom Server gelesen.",
        "fr": "L'état de {node} est lu par le serveur.",
        "it": "Lo stato di {node} viene letto dal server.",
        "ja": "{node} の状態はサーバーが読み取ります。",
        "zh": "{node} 的状态由服务器读取。",
        "pt": "O estado de {node} é lido pelo servidor.",
    },
    "query_off": {
        "en": "Questions about error codes are switched off on this system.",
        "es": "Las preguntas sobre códigos de error están desactivadas en este sistema.",
        "de": "Fragen zu Fehlercodes sind auf diesem System ausgeschaltet.",
        "fr": "Les questions sur les codes d'erreur sont désactivées sur ce système.",
        "it": "Le domande sui codici di errore sono disattivate su questo sistema.",
        "ja": "このシステムではエラーコードに関する質問は無効になっています。",
        "zh": "此系统已关闭对错误代码的提问。",
        "pt": "As perguntas sobre códigos de erro estão desativadas neste sistema.",
    },
    "query_not_found": {
        "en": "The documentation has no entry for the code {errcode}.",
        "es": "La documentación no tiene ninguna entrada para el código {errcode}.",
        "de": "Die Dokumentation enthält keinen Eintrag für den Code {errcode}.",
        "fr": "La documentation n'a aucune entrée pour le code {errcode}.",
        "it": "La documentazione non ha nessuna voce per il codice {errcode}.",
        "ja": "ドキュメントにコード {errcode} の項目はありません。",
        "zh": "文档中没有代码 {errcode} 的条目。",
        "pt": "A documentação não tem nenhuma entrada para o código {errcode}.",
    },
    "query_unavailable": {
        "en": "The documentation assistant did not answer, so I cannot look up the code {errcode} now.",
        "es": "El asistente de documentación no ha respondido, así que ahora no puedo consultar el código {errcode}.",
        "de": "Der Dokumentationsassistent hat nicht geantwortet, daher kann ich den Code {errcode} jetzt nicht nachschlagen.",
        "fr": "L'assistant de documentation n'a pas répondu, je ne peux donc pas consulter le code {errcode} maintenant.",
        "it": "L'assistente della documentazione non ha risposto, quindi ora non posso consultare il codice {errcode}.",
        "ja": "ドキュメントアシスタントが応答しないため、今はコード {errcode} を調べられません。",
        "zh": "文档助手没有响应，因此现在无法查询代码 {errcode}。",
        "pt": "O assistente de documentação não respondeu, por isso agora não posso consultar o código {errcode}.",
    },
    "query_answer": {
        "en": "Code {errcode}: {answer}",
        "es": "Código {errcode}: {answer}",
        "de": "Code {errcode}: {answer}",
        "fr": "Code {errcode} : {answer}",
        "it": "Codice {errcode}: {answer}",
        "ja": "コード {errcode}：{answer}",
        "zh": "代码 {errcode}：{answer}",
        "pt": "Código {errcode}: {answer}",
    },
    "alert_anomaly_suspect": {
        "en": "Attention: node {node} shows suspicious behaviour.",
        "es": "Atención: el nodo {node} muestra un comportamiento sospechoso.",
        "de": "Achtung: Knoten {node} zeigt verdächtiges Verhalten.",
        "fr": "Attention : le nœud {node} présente un comportement suspect.",
        "it": "Attenzione: il nodo {node} mostra un comportamento sospetto.",
        "ja": "注意：ノード {node} に不審な挙動があります。",
        "zh": "注意：节点 {node} 出现可疑行为。",
        "pt": "Atenção: o nó {node} apresenta um comportamento suspeito.",
    },
    "alert_anomaly_anomalous": {
        "en": "Warning: node {node} is behaving abnormally.",
        "es": "Aviso: el nodo {node} se comporta de forma anómala.",
        "de": "Warnung: Knoten {node} verhält sich anormal.",
        "fr": "Avertissement : le nœud {node} se comporte de façon anormale.",
        "it": "Avviso: il nodo {node} si comporta in modo anomalo.",
        "ja": "警告：ノード {node} が異常な動作をしています。",
        "zh": "警告：节点 {node} 行为异常。",
        "pt": "Aviso: o nó {node} comporta-se de forma anómala.",
    },
}


def language_of(locale: object) -> str:
    """The language of the eight that a locale asks for ("pt-PT" -> "pt", "zh_TW" -> "zh"); English otherwise."""
    if isinstance(locale, str):
        primary = locale.replace("_", "-").split("-", 1)[0].strip().lower()
        if primary in LANGUAGES:
            return primary
    return DEFAULT_LANGUAGE


def message(code: str, locale: object, **parameters: object) -> str:
    """The sentence `code` in the language of `locale`, with its placeholders filled."""
    catalog = MESSAGES[code]
    return catalog[language_of(locale)].format(**parameters)
