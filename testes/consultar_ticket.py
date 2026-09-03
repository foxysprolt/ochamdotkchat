import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AUVO_API_KEY", "SUA_API_KEY_AQUI")
API_TOKEN = os.getenv("AUVO_API_TOKEN", "SEU_API_TOKEN_AQUI")
TICKET_ID = os.getenv("TICKET_ID", "8086")

def consultar_ticket_resumido():
    print(f"=== CONSULTANDO TICKET #{TICKET_ID} (COM NOTAS E INTERAÇÕES) ===")
    
    # 1. Autenticação
    url_login = "https://api.auvo.com.br/v2/login"
    payload_login = {"apiKey": API_KEY, "apiToken": API_TOKEN}

    try:
        req_login = urllib.request.Request(
            url_login,
            data=json.dumps(payload_login).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req_login, timeout=10) as resp:
            token = json.loads(resp.read().decode("utf-8")).get("result", {}).get("accessToken")
    except Exception as err:
        print(f"❌ Erro no Login: {err}")
        return

    # 2. Requisição GET para o Ticket com flags de interações e modificações ativadas
    url_ticket = (
        f"https://api.auvo.com.br/v2/tickets/{TICKET_ID}"
        f"?searchInteractions=true&searchModifications=true&searchCustomFields=true"
    )
    headers = {"Authorization": f"Bearer {token}"}

    try:
        req = urllib.request.Request(url_ticket, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            dados_brutos = json.loads(resp.read().decode("utf-8")).get("result", {})
            
            if not dados_brutos:
                print("❌ Ticket não encontrado.")
                return

            # --- TRATAMENTO DOS CUSTOM FIELDS ---
            campos_personalizados = {}
            for item in dados_brutos.get("customFields", []):
                meta = item.get("customFieldTicket", {})
                titulo = meta.get("title")
                id_campo = meta.get("id")
                valor = item.get("value") or item.get("valueDescription") or ""
                campos_personalizados[f"{titulo} (ID: {id_campo})"] = valor

            # --- EXTRAÇÃO DE NOTAS INTERNAS E INTERAÇÕES ---
            notas_e_interacoes = []
            
            # Puxa o histórico de mensagens / notas criadas
            for interacao in dados_brutos.get("interactions", []):
                notas_e_interacoes.append({
                    "data": interacao.get("date") or interacao.get("creationDate"),
                    "autor": interacao.get("userName") or interacao.get("userCreatedName") or "Sistema",
                    "tipo": interacao.get("typeDescription", "Anotação/Resposta"),
                    "conteudo": interacao.get("message") or interacao.get("description") or ""
                })

            # --- EXTRAÇÃO DO HISTÓRICO DE ALTERAÇÕES ---
            historico_alteracoes = []
            for alt in dados_brutos.get("alterations", []):
                historico_alteracoes.append({
                    "tipo": alt.get("alterationType"),
                    "id_destino": alt.get("to"),
                    "descricao_destino": alt.get("toDescription")
                })

            # --- ESTRUTURAÇÃO DO JSON FINAL ---
            ticket_resumido = {
                "ticket_id": dados_brutos.get("id"),
                "titulo": dados_brutos.get("title"),
                "descricao": dados_brutos.get("description"),
                "status": dados_brutos.get("statusDescription"),
                "prioridade": dados_brutos.get("priority"),
                "propriedades_nativas": {
                    "teamId": dados_brutos.get("teamId"),
                    "teamName": dados_brutos.get("teamName"),
                    "requestTypeDescription": dados_brutos.get("requestTypeDescription"),
                    "userResponsableId": dados_brutos.get("userResponsableId")
                },
                "campos_customizados_preenchidos": campos_personalizados,
                "anotacoes_e_interacoes": notas_e_interacoes,
                "historico_ids_alterados": historico_alteracoes
            }

            print("\n✅ DADOS ESSENCIAIS DO TICKET:")
            print(json.dumps(ticket_resumido, indent=2, ensure_ascii=False))

    except Exception as err:
        print(f"❌ Erro na consulta: {err}")

if __name__ == "__main__":
    consultar_ticket_resumido()