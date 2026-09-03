import os
import re
import json
import time
import sqlite3
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURAÇÃO DE LOGS E AMBIENTE
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("oschamados.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

AUVO_API_KEY = os.getenv("AUVO_API_KEY")
AUVO_API_TOKEN = os.getenv("AUVO_API_TOKEN")

# Identificadores da conta do Bot para filtragem estrita de respostas
NOMES_CONTA_BOT = ["INTEGRAÇÃO", "INTEGRACAO", "POWER2GO BOT", "POWERBOT"]

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "hermes3:latest")

PROMPT_FILE = "prompt_hermes.txt"
DB_FILE = "oschamados.db"

# ==============================================================================
# GUARDRAILS E FILTROS DE SEGURANÇA
# ==============================================================================
STATUS_MONITORADOS = [
    "Agendado",
    "Aguardando Atendimento",
    "Em atendimento",
    "Pendente Cliente",
    "Pendente Power2Go",
    "Definir Solucao",
    "Pendente Orçamento"
]

FUNCIONARIOS_HUMANOS = [
    "RAFAEL FERNANDES DE ARRUDA",
    "LUCIANE BARAO GIARETTA",
    "FAGNER ABADE PASSOS",
    "DANIEL MAUAD GEBARA",
    "JEANE MOREIRA DE BRITO CERQUEIRA NERI",
    "RENATO GARGEL",
    "TATIANE DE MELO VIANA",
    "CLAUDIA DE ALMEIDA BARCHE",
    "RONALD DOS SANTOS CONCEICAO",
    "JOAO PAULO DOMINGOS DOS SANTOS",
    "JOSE EURICO DE SOUSA",
    "ENGENHARIA"
]

# ==============================================================================
# MAPA DE IDS REAIS EXTRAÍDOS DA SUA CONTA AUVO
# ==============================================================================
MAPEAMENTO_STATUS_ID = {
    "Agendado": 104284,
    "Aguardando Atendimento": 99949,
    "Em atendimento": 99950,
    "Pendente Cliente": 99951,
    "Pendente Power2Go": 99952,
    "Definir Solucao": 103792,
    "Pendente Orçamento": 109967,
    "Atendimento Cancelado": 99953,
    "Atendimento Encerrado": 99954,
    "Cancelado": 99953,
    "Resolvido": 99954
}

MAPEAMENTO_TIPOS_SOLICITACAO_ID = {
    # Nomes Nativos do Auvo
    "ANALISE DE CARREGADOR": 53984,
    "MANUTENCAO/ REDE": 52180,
    "MANUTENCAO/ INFRAESTRUTURA": 52181,
    "MANUTENCAO/ HARDWARE": 50809,
    "INFORMACOES/ USABILITY": 50811,
    "INFORMACOES DE CONTRATO/ ART": 54019,
    "VALOR DO KWH/ TAXA DE OCIOSIDADE": 54552,
    "VISITA INSPECAO/ IT41": 54647,
    
    # Aliases do Prompt Hermes
    "MANUTENCAO / REDE": 52180,
    "MANUTENCAO / INFRAESTRUTURA": 52181,
    "MANUTENCAO / HARDWARE": 50809,
    "REPARO EM GARANTIA": 50809,
    "INFORMACOES / USABILITY": 50811,
    "APLICATIVO": 50811,
    "CARTAO DE ACESSO": 50811,
    "SOLICITACAO DE CANCELAMENTO": 50811,
    "INFORMACOES DE CONTRATO / ART": 54019,
    "VALOR DO KWH": 54552,
    "TAXA DE OCIOSIDADE": 54552,
    "ESTORNO / REEMBOLSO": 54552,
    "RELATORIO": 54552,
    "BOLETO / 2º VIA / VENCIMENTO": 54552,
    "FINANCEIRO": 54552,
    "VISITA INSPECAO / IT41": 54647
}

MAPEAMENTO_ROTEAMENTO_ESPECIALISTAS = {
    "Rafael Arruda": {"user_id": 222960, "team_id": 7395},
    "Fagner Abade": {"user_id": 239409, "team_id": 7396},
    "Luciane Barão": {"user_id": 222959, "team_id": 7396},
    "Daniel Gebara": {"user_id": 221916, "team_id": 7395},
    "Jeane Brito": {"user_id": 195726, "team_id": 7790},
    "Renato Gargel": {"user_id": None, "team_id": 7790},
    "Engenharia de Execução": {"user_id": 207970, "team_id": 7397},
    "Tatiane Viana": {"user_id": 186011, "team_id": 7396}
}

# ==============================================================================
# 1. PERSISTÊNCIA LOCAL (SQLITE) & MÉTRICAS
# ==============================================================================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ciclo_cobranca (
                ticket_id INTEGER PRIMARY KEY,
                qtd_lembretes INTEGER DEFAULT 0,
                ultima_cobranca_timestamp TEXT,
                status_ciclo TEXT DEFAULT 'ATIVO'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metricas_diarias (
                data_iso TEXT PRIMARY KEY,
                total_triados INTEGER DEFAULT 0,
                total_defletidos INTEGER DEFAULT 0,
                total_roteados INTEGER DEFAULT 0,
                total_duplicados INTEGER DEFAULT 0,
                total_ignorados INTEGER DEFAULT 0,
                total_cobrados INTEGER DEFAULT 0,
                total_erros INTEGER DEFAULT 0
            )
        """)
        conn.commit()

def registrar_metrica(tipo_acao):
    hoje = datetime.now().strftime("%Y-%m-%d")
    colunas = {
        "TRIADO": "total_triados",
        "DEFLETIDO": "total_defletidos",
        "ROTEADO": "total_roteados",
        "DUPLICADO": "total_duplicados",
        "IGNORADO": "total_ignorados",
        "COBRADO": "total_cobrados",
        "ERRO": "total_erros"
    }
    coluna = colunas.get(tipo_acao)
    if not coluna:
        return

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO metricas_diarias (data_iso, total_triados, total_defletidos, total_roteados, total_duplicados, total_ignorados, total_cobrados, total_erros)
            VALUES (?, 0, 0, 0, 0, 0, 0, 0)
            ON CONFLICT(data_iso) DO NOTHING
        """, (hoje,))
        
        if tipo_acao != "ERRO":
            cursor.execute(f"UPDATE metricas_diarias SET {coluna} = {coluna} + 1, total_triados = total_triados + 1 WHERE data_iso = ?", (hoje,))
        else:
            cursor.execute(f"UPDATE metricas_diarias SET {coluna} = {coluna} + 1 WHERE data_iso = ?", (hoje,))
        conn.commit()

def obter_metricas_dia_atual():
    hoje = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT total_triados, total_defletidos, total_roteados, total_duplicados, total_ignorados, total_cobrados, total_erros FROM metricas_diarias WHERE data_iso = ?", (hoje,))
        row = cursor.fetchone()
        if not row:
            return {"total_triados": 0, "total_defletidos": 0, "total_roteados": 0, "total_duplicados": 0, "total_ignorados": 0, "total_cobrados": 0, "total_erros": 0}
        return {"total_triados": row[0], "total_defletidos": row[1], "total_roteados": row[2], "total_duplicados": row[3], "total_ignorados": row[4], "total_cobrados": row[5], "total_erros": row[6]}

def resetar_ciclo_cobranca(ticket_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ciclo_cobranca WHERE ticket_id = ?", (ticket_id,))
        conn.commit()

def processar_ciclo_cobranca_deterministico(ticket_id):
    agora = datetime.now()
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT qtd_lembretes, ultima_cobranca_timestamp FROM ciclo_cobranca WHERE ticket_id = ?", (ticket_id,))
        row = cursor.fetchone()

        if not row:
            cursor.execute("INSERT INTO ciclo_cobranca (ticket_id, qtd_lembretes, ultima_cobranca_timestamp, status_ciclo) VALUES (?, 1, ?, 'ATIVO')", (ticket_id, agora.isoformat()))
            conn.commit()
            return "LEMBRETE_1"

        qtd_lembretes, ultima_str = row
        ultima_data = datetime.fromisoformat(ultima_str)
        horas_decorridas = (agora - ultima_data).total_seconds() / 3600

        if horas_decorridas < 6:
            return "AGUARDAR"

        nova_qtd = qtd_lembretes + 1
        if nova_qtd >= 4:
            cursor.execute("UPDATE ciclo_cobranca SET status_ciclo = 'CONCLUIDO' WHERE ticket_id = ?", (ticket_id,))
            conn.commit()
            return "ENCERRAR_INATIVIDADE"
        else:
            cursor.execute("UPDATE ciclo_cobranca SET qtd_lembretes = ?, ultima_cobranca_timestamp = ? WHERE ticket_id = ?", (nova_qtd, agora.isoformat(), ticket_id))
            conn.commit()
            return f"LEMBRETE_{nova_qtd}"

# ==============================================================================
# 2. PARSING E DETECÇÃO TEMPORAL DE RESPOSTA DO CLIENTE
# ==============================================================================
def parse_iso_date_safe(data_str):
    if not data_str or not isinstance(data_str, str):
        return None
    try:
        clean_str = data_str.split(".")[0].replace("Z", "")
        return datetime.strptime(clean_str[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None

def verificar_resposta_cliente_apos_ultimo_lembrete(ticket_id, interacoes):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ultima_cobranca_timestamp FROM ciclo_cobranca WHERE ticket_id = ?", (ticket_id,))
        row = cursor.fetchone()

    if not row or not row[0]:
        return False

    ultima_cobranca_dt = datetime.fromisoformat(row[0])

    for inter in interacoes:
        data_inter = parse_iso_date_safe(inter.get("data"))
        if not data_inter:
            continue

        if data_inter > ultima_cobranca_dt:
            autor = (inter.get("autor") or "").upper().strip()
            msg = inter.get("mensagem") or ""

            is_humano = any(h in autor for h in FUNCIONARIOS_HUMANOS)
            is_bot = any(bot_name in autor for bot_name in NOMES_CONTA_BOT) or "[HERMES AI]" in msg or "SISTEMA" in autor

            if not is_humano and not is_bot:
                return True

    return False

def extrair_json_limpo(resposta_str):
    if not resposta_str:
        return None
    limpo = re.sub(r"```(?:json)?", "", resposta_str, flags=re.IGNORECASE).replace("```", "").strip()
    try:
        return json.loads(limpo)
    except json.JSONDecodeError:
        return None

def validar_schema_decisao(decisao):
    if not isinstance(decisao, dict):
        return False, "Saída não é JSON válido."
    acoes = {"ROTEAR", "RESPONDER_E_RESOLVER", "DUPLICIDADE", "IGNORAR"}
    action = decisao.get("action_type")
    if action not in acoes:
        return False, f"Ação inválida: {action}"
    if action == "DUPLICIDADE" and not decisao.get("ticket_principal_id"):
        return False, "Sem ticket_principal_id"
    if action == "RESPONDER_E_RESOLVER" and not decisao.get("mensagem_publica"):
        return False, "Sem mensagem_publica"
    return True, "OK"

# ==============================================================================
# 3. COMUNICAÇÃO API AUVO V2
# ==============================================================================
def autenticar_auvo():
    url = "https://api.auvo.com.br/v2/login"
    payload = {"apiKey": AUVO_API_KEY, "apiToken": AUVO_API_TOKEN}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")).get("result", {}).get("accessToken")
    except Exception as err:
        logging.error(f"Erro Autenticação Auvo: {err}")
        return None

def buscar_tickets_abertos(token):
    base_url = "https://api.auvo.com.br/v2/tickets"
    data_inicio = "2020-01-01T00:00:00"
    data_fim = datetime.now().strftime("%Y-%m-%dT23:59:59")
    filtro_obj = {"startDate": data_inicio, "endDate": data_fim, "searchTasks": False, "searchInteractions": False}
    params = {"paramFilter": json.dumps(filtro_obj), "page": 1, "pageSize": 50, "order": "desc"}
    url_final = f"{base_url}/?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        req = urllib.request.Request(url_final, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            lista = json.loads(resp.read().decode("utf-8")).get("result", {}).get("entityList", [])
            return [t for t in lista if t.get("statusDescription") in STATUS_MONITORADOS]
    except Exception as err:
        logging.error(f"Erro buscar tickets: {err}")
        return []

def consultar_detalhes_ticket(token, ticket_id):
    url = f"https://api.auvo.com.br/v2/tickets/{ticket_id}?searchInteractions=true&searchCustomFields=true"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            dados = json.loads(resp.read().decode("utf-8")).get("result", {})
            interacoes = []
            tem_humano = False
            
            for inter in dados.get("interactions", []):
                autor = (inter.get("userName") or "Sistema").upper().strip()
                if any(h in autor for h in FUNCIONARIOS_HUMANOS):
                    tem_humano = True
                interacoes.append({"data": inter.get("date") or inter.get("creationDate"), "autor": autor, "mensagem": inter.get("message") or ""})
                
            return {
                "id": dados.get("id"), "titulo": dados.get("title"), "status_nome": dados.get("statusDescription"),
                "categoria_atual": dados.get("requestTypeDescription"), "descricao": dados.get("description"),
                "interacoes": interacoes, "tem_nota_humana": tem_humano
            }
    except Exception as err:
        logging.error(f"Erro ao detalhar ticket #{ticket_id}: {err}")
        return None

def adicionar_interacao_auvo(token, ticket_id, mensagem, is_internal=False):
    url = f"https://api.auvo.com.br/v2/tickets/{ticket_id}/interactions"
    payload = {"message": mensagem, "isInternal": is_internal}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as err:
        logging.error(f"Erro interacao #{ticket_id}: {err}")
        return False

def atualizar_ticket_auvo(token, ticket_id, novo_status_nome=None, user_id=None, team_id=None, request_type_name=None):
    payload = {}
    
    if novo_status_nome and novo_status_nome in MAPEAMENTO_STATUS_ID:
        payload["statusId"] = MAPEAMENTO_STATUS_ID[novo_status_nome]
        
    if user_id:
        payload["userResponsableId"] = int(user_id)

    if team_id:
        payload["teamId"] = int(team_id)
        
    if request_type_name and request_type_name in MAPEAMENTO_TIPOS_SOLICITACAO_ID:
        payload["requestTypeId"] = MAPEAMENTO_TIPOS_SOLICITACAO_ID[request_type_name]

    if not payload:
        return False

    url = f"https://api.auvo.com.br/v2/tickets/{ticket_id}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as err:
        logging.error(f"Erro PATCH #{ticket_id}: {err}")
        return False

# ==============================================================================
# 4. INTELIGÊNCIA IA LOCAL (HERMES / OLLAMA)
# ==============================================================================
def consultar_hermes_local(detalhes_ticket):
    if not os.path.exists(PROMPT_FILE):
        logging.error(f"Prompt '{PROMPT_FILE}' não encontrado!")
        return None

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_sistema = f.read()

    payload_input = {
        "ticket_id": detalhes_ticket["id"], "titulo": detalhes_ticket["titulo"],
        "categoria_atual": detalhes_ticket["categoria_atual"], "descricao_cliente": detalhes_ticket["descricao"],
        "historico_interacoes": detalhes_ticket["interacoes"]
    }
    
    prompt_final = f"{prompt_sistema}\n\nANALISE O TICKET:\n{json.dumps(payload_input, ensure_ascii=False, indent=2)}\n\nRESPOSTA (JSON APENAS):"
    request_body = {"model": OLLAMA_MODEL, "prompt": prompt_final, "format": "json", "stream": False, "options": {"temperature": 0.1}}

    try:
        req = urllib.request.Request(OLLAMA_API_URL, data=json.dumps(request_body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            res_raw = json.loads(resp.read().decode("utf-8")).get("response", "")
            decisao = extrair_json_limpo(res_raw)
            valido, motivo = validar_schema_decisao(decisao)
            if not valido:
                logging.warning(f"Resposta do Hermes inválida para ticket #{detalhes_ticket['id']}: {motivo}")
                return None
            return decisao
    except Exception as err:
        logging.error(f"Erro Ollama ticket #{detalhes_ticket['id']}: {err}")
        return None

# ==============================================================================
# 5. GERADOR DO RELATÓRIO DIÁRIO (IDEMPOTENTE E PAGINADO)
# ==============================================================================
def auditar_backlog_estagnado(token):
    base_url = "https://api.auvo.com.br/v2/tickets"
    data_inicio = "2020-01-01T00:00:00"
    data_fim = datetime.now().strftime("%Y-%m-%dT23:59:59")
    filtro_obj = {"startDate": data_inicio, "endDate": data_fim, "searchTasks": False}
    params = {"paramFilter": json.dumps(filtro_obj), "page": 1, "pageSize": 100, "order": "desc"}
    url_final = f"{base_url}/?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    tickets_estagnados = []
    try:
        req = urllib.request.Request(url_final, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            lista = json.loads(resp.read().decode("utf-8")).get("result", {}).get("entityList", [])
            limite = datetime.now() - timedelta(days=7)

            for t in lista:
                if t.get("statusDescription") in STATUS_MONITORADOS:
                    dt_mov = parse_iso_date_safe(t.get("lastModificationDate") or t.get("creationDate"))
                    if dt_mov and dt_mov < limite:
                        dias = (datetime.now() - dt_mov).days
                        tickets_estagnados.append({"id": t.get("id"), "titulo": t.get("title"), "dias_parado": dias, "responsavel": t.get("orientationUser") or "Sem Atribuição"})
    except Exception as err:
        logging.error(f"Erro auditoria backlog: {err}")
    return tickets_estagnados

def checar_relatorio_ja_gerado_hoje(token, titulo):
    base_url = "https://api.auvo.com.br/v2/tickets"
    data_hoje = datetime.now().strftime("%Y-%m-%dT00:00:00")
    filtro_obj = {"startDate": data_hoje, "endDate": datetime.now().strftime("%Y-%m-%dT23:59:59"), "searchTasks": False}
    params = {"paramFilter": json.dumps(filtro_obj), "page": 1, "pageSize": 100, "order": "desc"}
    url_final = f"{base_url}/?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(url_final, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            lista = json.loads(resp.read().decode("utf-8")).get("result", {}).get("entityList", [])
            return any(t.get("title") == titulo for t in lista)
    except Exception as err:
        logging.error(f"Erro checagem idempotência relatório: {err}")
        return False

def executar_relatorio_diario_consolidado():
    logging.info("=== 📊 GERANDO RELATÓRIO DIÁRIO DE OPERAÇÃO ===")
    token = autenticar_auvo()
    if not token:
        return

    titulo_relatorio = f"📊 Relatório Diário de Operação OSChamados - {datetime.now().strftime('%d/%m/%Y')}"
    if checar_relatorio_ja_gerado_hoje(token, titulo_relatorio):
        logging.warning("Relatório diário já foi gerado hoje. Cancelando duplicidade.")
        return

    metricas = obter_metricas_dia_atual()
    estagnados = auditar_backlog_estagnado(token)

    corpo = [
        f"🤖 RESUMO DE OPERAÇÃO BACKOFFICE - OSCHAMADOS",
        f"Data: {datetime.now().strftime('%d/%m/%Y às %H:%M')}\n",
        f"--- MÉTRICAS REAIS DO DIA ---",
        f"• Total de Chamados Processados: {metricas['total_triados']}",
        f"• Deflexões / Resolvidos: {metricas['total_defletidos']}",
        f"• Roteados para Especialistas: {metricas['total_roteados']}",
        f"• Lembretes de Cobrança Enviados: {metricas['total_cobrados']}",
        f"• Duplicidades Encerradas: {metricas['total_duplicados']}",
        f"• Ignorados (Atendimento Humano): {metricas['total_ignorados']}",
        f"• Erros / Falhas de IA: {metricas['total_erros']}\n",
        f"--- AUDITORIA DE BACKLOG (>7 DIAS PARADOS) ---",
        f"Total de chamados estagnados: {len(estagnados)}\n"
    ]

    if estagnados:
        corpo.append("MAIS CRÍTICOS:")
        for t in estagnados[:10]:
            corpo.append(f"• ID #{t['id']} | Parado há {t['dias_parado']}d | Resp: {t['responsavel']} | {t['titulo']}")
    else:
        corpo.append("✅ Nenhum chamado parado há mais de 7 dias.")

    url = "https://api.auvo.com.br/v2/tickets"
    payload = {"title": titulo_relatorio, "description": "\n".join(corpo), "requestTypeDescription": "RELATORIO", "orientationUser": "EQUIPE OPERACIONAL"}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8")).get("result", {})
            logging.info(f"✅ Ticket de Relatório Diário criado! ID #{res.get('id')}")
    except Exception as err:
        logging.error(f"Erro ao publicar ticket de relatório: {err}")

# ==============================================================================
# 6. WORKER DE TRIAGEM & COBRANÇA DETERMINÍSTICA ROBUSTA
# ==============================================================================
def processar_motor_oschamados():
    logging.info("=== 🤖 PROCESSANDO TRIAGEM DA FILA ===")
    token = autenticar_auvo()
    if not token:
        return

    tickets = buscar_tickets_abertos(token)
    for t_resumo in tickets:
        t_id = t_resumo.get("id")
        detalhes = consultar_detalhes_ticket(token, t_id)
        if not detalhes:
            continue

        if detalhes["tem_nota_humana"]:
            registrar_metrica("IGNORADO")
            time.sleep(0.3)
            continue

        # TRATAMENTO DETERMINÍSTICO DE COBRANÇA (STATUS PENDENTE CLIENTE)
        if detalhes["status_nome"] == "Pendente Cliente":
            cliente_respondeu = verificar_resposta_cliente_apos_ultimo_lembrete(t_id, detalhes["interacoes"])
            
            if cliente_respondeu:
                logging.info(f"📩 Resposta real do cliente identificada no ticket #{t_id}. Resetando cobrança e retriando...")
                resetar_ciclo_cobranca(t_id)
                atualizar_ticket_auvo(token, t_id, novo_status_nome="Em atendimento")
                detalhes["status_nome"] = "Em atendimento"
            else:
                etapa = processar_ciclo_cobranca_deterministico(t_id)
                if etapa == "AGUARDAR":
                    logging.info(f"⏳ Ticket #{t_id} aguardando janela de 6h do lembrete.")
                elif etapa == "ENCERRAR_INATIVIDADE":
                    msg_fim = "Atendimento encerrado automaticamente devido à ausência de retorno após 24 horas."
                    adicionar_interacao_auvo(token, t_id, msg_fim, is_internal=False)
                    atualizar_ticket_auvo(token, t_id, novo_status_nome="Cancelado")
                    registrar_metrica("DEFLETIDO")
                    logging.info(f"🔒 Ticket #{t_id} encerrado por inatividade de 24h.")
                else:
                    msg_lembrete = "Olá! Identificamos que você ainda não respondeu à nossa última mensagem. Precisamos da sua confirmação para prosseguir com o atendimento."
                    adicionar_interacao_auvo(token, t_id, msg_lembrete, is_internal=False)
                    atualizar_ticket_auvo(token, t_id, novo_status_nome="Pendente Cliente")
                    registrar_metrica("COBRADO")
                    logging.info(f"📣 Lembrete ({etapa}) enviado para o ticket #{t_id}.")
                
                time.sleep(0.5)
                continue

        # TRIAGEM VIA HERMES LOCAL
        decisao = consultar_hermes_local(detalhes)
        if not decisao:
            registrar_metrica("ERRO")
            time.sleep(0.3)
            continue

        action = decisao.get("action_type")
        responsavel = decisao.get("responsavel_recomendado")
        msg_publica = decisao.get("mensagem_publica")
        nota_interna = decisao.get("nota_interna")
        novo_status = decisao.get("novo_status")
        req_type = decisao.get("request_type_description")

        if action == "IGNORAR":
            registrar_metrica("IGNORADO")
            time.sleep(0.3)
            continue

        if nota_interna:
            adicionar_interacao_auvo(token, t_id, f"[HERMES AI]: {nota_interna}", is_internal=True)

        if action == "RESPONDER_E_RESOLVER" and msg_publica:
            adicionar_interacao_auvo(token, t_id, msg_publica, is_internal=False)
            atualizar_ticket_auvo(token, t_id, novo_status_nome="Resolvido", request_type_name=req_type)
            registrar_metrica("DEFLETIDO")

        elif action == "DUPLICIDADE":
            ticket_pai = decisao.get("ticket_principal_id")
            adicionar_interacao_auvo(token, t_id, f"Unificado no ticket principal #{ticket_pai}.", is_internal=False)
            atualizar_ticket_auvo(token, t_id, novo_status_nome="Cancelado")
            registrar_metrica("DUPLICADO")

        elif action == "ROTEAR":
            dados_roteamento = MAPEAMENTO_ROTEAMENTO_ESPECIALISTAS.get(responsavel, {})
            user_id = dados_roteamento.get("user_id")
            team_id = dados_roteamento.get("team_id")

            atualizar_ticket_auvo(
                token, 
                t_id, 
                novo_status_nome=novo_status, 
                user_id=user_id,
                team_id=team_id, 
                request_type_name=req_type
            )
            registrar_metrica("ROTEADO")

        time.sleep(0.5)

# ==============================================================================
# 7. EXECUTOR PRINCIPAL (LOOP 24/7 ROBUSTO POR DATA)
# ==============================================================================
def rodar_sistema():
    init_db()
    logging.info("🚀 OSCHAMADOS ENGINE UNIFICADO INICIADO")
    data_ultimo_relatorio = None

    while True:
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        hora_atual = datetime.now().strftime("%H:%M")

        # 1. Executa Triagem e Cobrança
        try:
            processar_motor_oschamados()
        except Exception as e:
            logging.error(f"Erro não tratado no ciclo de triagem: {e}", exc_info=True)

        # 2. Executa Relatório Diário com controle estrito por data
        if hora_atual >= "18:00" and data_ultimo_relatorio != data_hoje:
            try:
                executar_relatorio_diario_consolidado()
                data_ultimo_relatorio = data_hoje
            except Exception as e:
                logging.error(f"Erro no relatório diário: {e}", exc_info=True)

        time.sleep(600)

if __name__ == "__main__":
    rodar_sistema()