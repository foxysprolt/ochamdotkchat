import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import functions_framework
from flask import jsonify
from google import genai
from google.genai import types
import promptia

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Constantes ─────────────────────────────────────────────────────────────────
MODEL_NAME = "gemini-3.5-flash-lite"
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# ── Helpers ────────────────────────────────────────────────────────────────────

def enviar_email_via_gmail(conteudo_ticket, assunto_dinamico):
    remetente    = os.getenv("GMAIL_USER")
    senha_app    = os.getenv("GMAIL_APP_PASS")
    destinatario = "suporte@power2go.com.br"

    if not remetente or not senha_app:
        logger.error("Credenciais GMAIL_USER / GMAIL_APP_PASS nao configuradas.")
        return False

    senha_limpa = senha_app.replace(" ", "").strip()

    try:
        msg = MIMEMultipart()
        msg["From"]    = remetente
        msg["To"]      = destinatario
        msg["Subject"] = assunto_dinamico
        msg.attach(MIMEText(conteudo_ticket, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(remetente, senha_limpa)
            server.sendmail(remetente, destinatario, msg.as_string())

        logger.info("E-mail enviado com sucesso para %s", destinatario)
        return True

    except Exception as exc:
        logger.error("Erro ao enviar e-mail: %s", exc)
        return False


def extrair_assunto_ticket(ticket_texto):
    for l_ticket in ticket_texto.split("\n"):
        if "NOME DO LOCAL" in l_ticket.upper():
            partes = l_ticket.split(":", 1)
            if len(partes) > 1:
                valor = partes[1].strip()
                if valor and "[" not in valor:
                    return valor
    return "[CHAMADO DE SUPORTE] Power2Go"


def montar_historico_gemini(historico_bruto):
    historico = []
    for msg in historico_bruto:
        role_correta = "model" if msg.get("role") in ["bot", "model", "assistant"] else "user"
        historico.append(
            types.Content(
                role=role_correta,
                parts=[types.Part.from_text(text=msg.get("content", ""))]
            )
        )
    return historico


def disparar_email(resposta_texto):
    """Extrai assunto e envia o e-mail. Retorna (resposta_limpa, enviado)."""
    resposta_limpa = resposta_texto.replace("[DISPARAR_EMAIL]", "").strip()
    assunto_final  = extrair_assunto_ticket(resposta_limpa)
    enviado        = enviar_email_via_gmail(resposta_limpa, assunto_final)
    return resposta_limpa, enviado


# ── Entry-point ────────────────────────────────────────────────────────────────

@functions_framework.http
def chat_ochamado(request):
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
        }
        return ("", 204, headers)

    headers = {"Access-Control-Allow-Origin": "*"}

    try:
        dados = request.get_json(silent=True)
        if not dados or "historico" not in dados:
            return (jsonify({"erro": "Historico ausente"}), 400, headers)

        historico_bruto = dados.get("historico", [])
        if not historico_bruto:
            return (jsonify({"erro": "Historico vazio"}), 400, headers)

        # ── Delegação total do fluxo para o Gemini ──────────────────────────────
        historico_gemini = montar_historico_gemini(historico_bruto)

        instrucao_com_gatilho = (
            promptia.INSTRUCAO_SISTEMA +
            "\n\n[INSTRUCAO CRITICA DO SISTEMA]: Se o atendimento exigir abertura de chamado "
            "(o procedimento nao funcionou ou o cliente pediu suporte), "
            "verifique PRIMEIRO se possui Nome, Local, Telefone e E-mail/CPF. Se faltar algo, pergunte. "
            "Somente quando TUDO estiver preenchido, gere o modelo de ticket e inclua a tag [DISPARAR_EMAIL] isolada no final."
        )

        config_conversa = types.GenerateContentConfig(
            system_instruction=instrucao_com_gatilho,
            temperature=0.3,
        )
        completion = client.models.generate_content(
            model=MODEL_NAME,
            contents=historico_gemini,
            config=config_conversa,
        )
        resposta_final = completion.text

        # ── Intercepta tag do Gemini e dispara o email ─────────────────────────
        if "[DISPARAR_EMAIL]" in resposta_final:
            logger.info("Gatilho Gemini reconhecido: [DISPARAR_EMAIL] detectado.")
            resposta_limpa, email_enviado = disparar_email(resposta_final)
            
            if email_enviado:
                return (jsonify({"resposta": resposta_limpa}), 200, headers)
            else:
                resposta_com_aviso = (
                    resposta_limpa +
                    "\n\n*(Nota: O chamado foi gerado mas houve uma instabilidade no envio automático.)*"
                )
                return (jsonify({"resposta": resposta_com_aviso}), 200, headers)

        # Resposta de conversa normal
        return (jsonify({"resposta": resposta_final}), 200, headers)

    except Exception as exc:
        logger.exception("Erro interno nao tratado")
        return (jsonify({"erro": f"Erro interno: {str(exc)}"}), 500, headers)
