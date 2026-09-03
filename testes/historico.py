import os
import json
import urllib.parse
import urllib.request
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AUVO_API_KEY")
API_TOKEN = os.getenv("AUVO_API_TOKEN")

# Status que consideramos ABERTOS (para ignorá-loc na extração de encerrados)
STATUS_ABERTOS = [
    "Agendado", "Aguardando Atendimento", "Em atendimento", 
    "Orcamento nao aprovado", "Pendente Cliente", "Pendente Power2Go"
]

# Tipos de solicitação que não queremos no nosso arquivo de treinamento
TIPOS_IGNORADOS = [
    "instalação", "instalacao", "estudo de demanda", 
    "visita inpeção/it41", "visita inspeção/it41", "visita inspeção / it41"
]

def autenticar_auvo():
    url = "https://api.auvo.com.br/v2/login"
    payload = {"apiKey": API_KEY, "apiToken": API_TOKEN}
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8")).get("result", {}).get("accessToken")
    except Exception as err:
        print(f"❌ Erro na Autenticação: {err}")
        return None

def extrair_historico_para_treinamento(limite=1000):
    token = autenticar_auvo()
    if not token:
        return

    base_url = "https://api.auvo.com.br/v2/tickets"
    data_inicio = "2020-01-01T00:00:00"
    data_fim = datetime.now().strftime("%Y-%m-%dT23:59:59")
    
    page = 1
    page_size = 50
    historico_extraido = []
    
    print("=== 🧠 INICIANDO EXTRAÇÃO DE TREINAMENTO (1.000 TICKETS) ===")

    while len(historico_extraido) < limite:
        filtro_obj = {
            "startDate": data_inicio, "endDate": data_fim,
            "searchTasks": False, "searchInteractions": True # Puxamos as interações para a IA ler as respostas!
        }
        
        params = {
            "paramFilter": json.dumps(filtro_obj),
            "page": page, "pageSize": page_size, "order": "desc"
        }
        
        query_string = urllib.parse.urlencode(params)
        url_final = f"{base_url}/?{query_string}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            req = urllib.request.Request(url_final, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                lista_pagina = json.loads(resp.read().decode("utf-8")).get("result", {}).get("entityList", [])
                
                if not lista_pagina:
                    break # Acabaram os tickets na API
                
                for ticket in lista_pagina:
                    status = ticket.get("statusDescription", "")
                    tipo_req = str(ticket.get("requestTypeDescription", "")).lower().strip()
                    
                    # Filtra: Só pega se NÃO estiver aberto e NÃO for dos tipos ignorados
                    is_aberto = status in STATUS_ABERTOS
                    is_tipo_ignorado = any(ignorado in tipo_req for ignorado in TIPOS_IGNORADOS)
                    
                    if not is_aberto and not is_tipo_ignorado:
                        historico_extraido.append({
                            "id": ticket.get("id"),
                            "titulo": ticket.get("title"),
                            "categoria": ticket.get("requestTypeDescription"),
                            "descricao_cliente": ticket.get("description"),
                            # Pegando o histórico de conversa
                            "notas_e_mensagens": [
                                f"{nota.get('userName', 'Cliente')}: {nota.get('message', '')}" 
                                for nota in ticket.get("interactions", [])
                            ]
                        })
                        
                        if len(historico_extraido) >= limite:
                            break

                print(f"📄 Varrendo página {page}... (Coletados: {len(historico_extraido)}/{limite})")
                page += 1

        except Exception as err:
            print(f"❌ Erro ao puxar página {page}: {err}")
            break

    # Salva tudo em um arquivo JSON para enviar à IA
    with open("historico_treinamento.json", "w", encoding="utf-8") as f:
        json.dump(historico_extraido, f, ensure_ascii=False, indent=2)

    print(f"\n✅ SUCESSO! Arquivo 'historico_treinamento.json' criado com {len(historico_extraido)} tickets.")
    print("👉 Envie este arquivo aqui no chat para que eu possa aprender as resoluções da equipe!")

if __name__ == "__main__":
    extrair_historico_para_treinamento()