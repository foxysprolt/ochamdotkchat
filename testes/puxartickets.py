import os
import json
import urllib.parse
import urllib.request
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AUVO_API_KEY")
API_TOKEN = os.getenv("AUVO_API_TOKEN")

def autenticar_auvo():
    """Realiza o login na API v2 do Auvo e retorna o accessToken."""
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

def puxar_tickets_em_aberto(page=1, page_size=20):
    """
    Busca a lista de tickets incluindo os parâmetros obrigatórios startDate e endDate[cite: 1].
    """
    token = autenticar_auvo()
    if not token:
        print("❌ Não foi possível obter o token de acesso.")
        return []

    base_url = "https://api.auvo.com.br/v2/tickets"
    
    # O Auvo exige startDate e endDate preenchidos obrigatoriamente no paramFilter
    data_inicio = "2020-01-01T00:00:00"
    data_fim = datetime.now().strftime("%Y-%m-%dT23:59:59")
    
    filtro_obj = {
        "startDate": data_inicio,
        "endDate": data_fim,
        "searchTasks": False,
        "searchInteractions": False,
        "searchModifications": False,
        "searchCustomFields": False
    }
    
    param_filter_str = json.dumps(filtro_obj)
    
    params = {
        "paramFilter": param_filter_str,
        "page": page,
        "pageSize": page_size,
        "order": "desc"
    }
    
    query_string = urllib.parse.urlencode(params)
    url_final = f"{base_url}/?{query_string}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request(url_final, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resposta = json.loads(resp.read().decode("utf-8")).get("result", {})
            
            lista_tickets = resposta.get("entityList", [])
            total = resposta.get("pagedSearchReturnData", {}).get("totalItems", len(lista_tickets))

            print(f"✅ Sucesso! Total de tickets encontrados: {total}")
            return lista_tickets

    except urllib.error.HTTPError as err:
        print(f"❌ Erro HTTP {err.code}: {err.reason}")
        corpo_erro = err.read().decode("utf-8")
        print(f"Detalhes do servidor Auvo: {corpo_erro}")
        return []
    except Exception as err:
        print(f"❌ Erro inesperado: {err}")
        return []

if __name__ == "__main__":
    print("=== INICIANDO VARREDURA DE TICKETS (OSCHAMADOS) ===")
    tickets = puxar_tickets_em_aberto(page=1, page_size=10)
    
    if tickets:
        print("\n✅ LISTA DE TICKETS ENCONTRADOS:")
        for t in tickets:
            print(f"• ID #{t.get('id')} | Status: {t.get('statusDescription')} (ID: {t.get('statusId')}) | Título: {t.get('title')}")