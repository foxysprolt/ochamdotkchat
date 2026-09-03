import os
import json
import urllib.request

API_KEY = os.getenv("AUVO_API_KEY", "SUA_API_KEY_AQUI")
API_TOKEN = os.getenv("AUVO_API_TOKEN", "SEU_API_TOKEN_AQUI")

def testar_tipo():
    print("=== TESTE DE TIPO DE SOLICITAÇÃO NA BARRA LATERAL ===")
    
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
            print("✅ Autenticado com sucesso!\n")
    except Exception as err:
        print(f"❌ Erro no Login: {err}")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 2. Envio com typeId e requestTypeId na raiz
    url_tickets = "https://api.auvo.com.br/v2/tickets"

    payload_ticket = {
        "title": "SUPORTE: Teste Propriedade Tipo - PowerBot",
        "description": "Verificando preenchimento do Tipo de Solicitação na barra lateral.",
        "priority": 2,
        "statusId": 99950,
        "teamId": 7396,          # Equipe ATENDIMENTO (Funcionando)
        "typeId": 53984,          # ID numérico do Tipo (ANALISE DE CARREGADOR)
        "requestTypeId": 53984,   # Campo alternativo da raiz
        "customFields": [
            {
                "customFieldTicket": {"id": 163884},
                "value": "7396"
            },
            {
                "customFieldTicket": {"id": 163881},
                "value": "53984"
            },
            {
                "customFieldTicket": {"id": 170061},
                "value": "Cliente Teste"
            },
            {
                "customFieldTicket": {"id": 169446},
                "value": "(11) 98888-7777"
            },
            {
                "customFieldTicket": {"id": 169721},
                "value": "teste@email.com"
            }
        ]
    }

    try:
        req_ticket = urllib.request.Request(
            url_tickets,
            data=json.dumps(payload_ticket).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req_ticket, timeout=15) as resp_ticket:
            resposta = json.loads(resp_ticket.read().decode("utf-8"))
            ticket_id = resposta.get("result", {}).get("id")
            print(f"✅ Ticket #{ticket_id} criado!")
            print(json.dumps(resposta, indent=2))

    except urllib.error.HTTPError as err:
        print(f"❌ Erro HTTP ao criar ticket ({err.code}): {err.read().decode('utf-8')}")
    except Exception as err:
        print(f"❌ Erro inesperado: {err}")

if __name__ == "__main__":
    testar_tipo()