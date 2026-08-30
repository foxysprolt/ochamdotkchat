import os
import json
import urllib.request

API_KEY = os.getenv("AUVO_API_KEY", "SUA_API_KEY_AQUI")
API_TOKEN = os.getenv("AUVO_API_TOKEN", "SEU_API_TOKEN_AQUI")
TICKET_ID = "8086"  # Coloque aqui o ID do ticket que deseja consultar

def consultar_ticket_resumido():
    print(f"=== CONSULTANDO TICKET #{TICKET_ID} (RESUMO) ===")
    
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

    # 2. Requisição GET para o Ticket
    url_ticket = f"https://api.auvo.com.br/v2/tickets/{TICKET_ID}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        req = urllib.request.Request(url_ticket, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            dados_brutos = json.loads(resp.read().decode("utf-8")).get("result", {})
            
            # --- TRATAMENTO DOS CUSTOM FIELDS ---
            # Transforma o array gigante de customFields num dicionário limpo {"Nome do Campo": "Valor"}
            campos_personalizados = {}
            for item in dados_brutos.get("customFields", []):
                meta = item.get("customFieldTicket", {})
                titulo = meta.get("title")
                id_campo = meta.get("id")
                valor = item.get("value") or item.get("valueDescription") or ""
                
                # Guarda o nome, ID interno e o valor cadastrado
                campos_personalizados[f"{titulo} (ID: {id_campo})"] = valor

            # --- EXTRAÇÃO DO HISTÓRICO DE ALTERAÇÕES DE TIPO/EQUIPE ---
            alteracoes_importantes = []
            for alt in dados_brutos.get("alterations", []):
                alteracoes_importantes.append({
                    "tipo": alt.get("alterationType"),
                    "id_destino": alt.get("to"),
                    "descricao_destino": alt.get("toDescription")
                })

            # --- ESTRUTURAÇÃO DO JSON BONITINHO E RESUMIDO ---
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
                "historico_ids_alterados": alteracoes_importantes
            }

            print("\n✅ DADOS ESSENCIAIS DO TICKET:")
            print(json.dumps(ticket_resumido, indent=2, ensure_ascii=False))

    except Exception as err:
        print(f"❌ Erro na consulta: {err}")

if __name__ == "__main__":
    consultar_ticket_resumido()