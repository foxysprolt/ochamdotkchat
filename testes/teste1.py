import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

AUVO_API_KEY = os.getenv("AUVO_API_KEY")
AUVO_API_TOKEN = os.getenv("AUVO_API_TOKEN")
TICKET_ID = 8086

def autenticar_auvo():
    url = "https://api.auvo.com.br/v2/login"
    payload = {"apiKey": AUVO_API_KEY, "apiToken": AUVO_API_TOKEN}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8")).get("result", {}).get("accessToken")

def testar_patch_campo(token, nome_campo, path_patch, valor):
    url = f"https://api.auvo.com.br/v2/tickets/{TICKET_ID}"
    payload = [{"op": "replace", "path": path_patch, "value": valor}]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="PATCH")
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"✅ SUCESSO | Campo '{nome_campo}' ({path_patch}) aceito com valor {valor} (HTTP {resp.status})")
            return True
    except urllib.error.HTTPError as e:
        corpo = e.read().decode("utf-8", errors="replace")
        print(f"❌ FALHOU  | Campo '{nome_campo}' ({path_patch}) recusado (HTTP {e.code}): {corpo[:150]}")
    except Exception as e:
        print(f"❌ ERRO    | Campo '{nome_campo}' ({path_patch}): {e}")
    return False

def executar_varredura_patch():
    print(f"🚀 TESTANDO WHITELIST DE CAMPOS EDITÁVEIS VIA PATCH - TICKET #{TICKET_ID}\n")
    token = autenticar_auvo()
    if not token:
        print("❌ Falha na autenticação.")
        return

    # 1. Status (Sabemos que funciona)
    testar_patch_campo(token, "Status", "/statusId", 99952)

    # 2. Equipe / Departamento
    testar_patch_campo(token, "Equipe", "/teamId", 7396)

    # 3. Usuário Responsável
    testar_patch_campo(token, "Usuário Responsável", "/userResponsableId", 222960)

    # 4. Tipo de Solicitação / Categoria
    testar_patch_campo(token, "Tipo de Solicitação", "/requestTypeId", 53984)

    # 5. Prioridade
    testar_patch_campo(token, "Prioridade", "/priority", 2)

if __name__ == "__main__":
    executar_varredura_patch()