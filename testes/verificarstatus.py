import os
import json
import urllib.parse
import urllib.request
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AUVO_API_KEY")
API_TOKEN = os.getenv("AUVO_API_TOKEN")

STATUS_PERMITIDOS = [
    "Agendado",
    "Aguardando Atendimento",
    "Em atendimento",
    "Orcamento nao aprovado",
    "Pendente Cliente",
    "Pendente Power2Go"
]

def autenticar_auvo():
    url = "https://api.auvo.com.br/v2/login"
    payload = {"apiKey": API_KEY, "apiToken": API_TOKEN}
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resultado = json.loads(resp.read().decode("utf-8"))
            return resultado.get("result", {}).get("accessToken")
    except Exception as err:
        print(f"❌ Erro na Autenticação: {err}")
        return None

def puxar_todos_os_tickets_abertos():
    token = autenticar_auvo()
    if not token:
        return

    base_url = "https://api.auvo.com.br/v2/tickets"
    data_inicio = "2020-01-01T00:00:00"
    data_fim = datetime.now().strftime("%Y-%m-%dT23:59:59")
    
    page = 1
    page_size = 100
    todos_abertos = []
    
    print("=== 🤖 OSCHAMADOS - VARRENDO TODA A BASE DE TICKETS ===")

    while True:
        filtro_obj = {
            "startDate": data_inicio,
            "endDate": data_fim,
            "searchTasks": False,
            "searchInteractions": False
        }
        
        params = {
            "paramFilter": json.dumps(filtro_obj),
            "page": page,
            "pageSize": page_size,
            "order": "desc"
        }
        
        query_string = urllib.parse.urlencode(params)
        url_final = f"{base_url}/?{query_string}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            req = urllib.request.Request(url_final, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                resposta = json.loads(resp.read().decode("utf-8")).get("result", {})
                lista_pagina = resposta.get("entityList", [])
                
                if not lista_pagina:
                    break
                
                for ticket in lista_pagina:
                    status = ticket.get("statusDescription", "")
                    if status in STATUS_PERMITIDOS:
                        todos_abertos.append(ticket)

                print(f"📄 Página {page} processada... ({len(todos_abertos)} abertos encontrados até agora)")
                
                # Se trouxer menos itens que o tamanho da página, significa que chegou ao fim
                if len(lista_pagina) < page_size:
                    break
                    
                page += 1

        except Exception as err:
            print(f"❌ Erro na paginação: {err}")
            break

    print(f"\n✅ VARREDURA CONCLUÍDA!")
    print(f"🎯 Total de tickets realmente EM ABERTO na sua base: {len(todos_abertos)}")
    
    return todos_abertos

if __name__ == "__main__":
    puxar_todos_os_tickets_abertos()