# ⚡ PowerBot — Sistema de Suporte Técnico Inteligente | Power2Go

![Project Status](https://img.shields.io/badge/status-production-brightgreen)
![Python](https://img.shields.io/badge/python-3.11-blue)
![AI Model](https://img.shields.io/badge/LLM-Gemini%203.5%20Flash--Lite-orange)
![Frontend](https://img.shields.io/badge/hosting-GitHub%20Pages-black)
![GCP](https://img.shields.io/badge/backend-Google%20Cloud%20Run-google)

O **PowerBot** é o assistente virtual de inteligência artificial da **Power2Go**, desenvolvido para automatizar o atendimento inicial, realizar diagnósticos técnicos de primeiro nível e gerenciar a abertura de chamados de suporte para carregadores de veículos elétricos (EVs).

O sistema opera de forma agêntica em 3 etapas: realiza a triagem de dados do cliente, guia o usuário em testes físicos no equipamento (reset de disjuntor DR e leitura de LEDs) e, caso o problema persista, coleta de forma obrigatória os dados de contato completos para disparar um ticket padronizado via e-mail.

---

## 📁 Estrutura do Repositório

O repositório é organizado de forma modular, separando a interface pública (servida via GitHub Pages) da API serverless no Google Cloud:

```text
ochamadotkchat/
├── .gitignore             # Arquivo de proteção contra vazamento de credenciais (.env)
├── README.md              # Documentação principal do projeto
├── index.html             # Estrutura do Chat de Atendimento
├── script.js              # Lógica do front-end e requisições HTTP (Fetch API)
├── styles.css             # Estilização responsiva no padrão visual da marca
│
└── backend/                 # API Serverless (Google Cloud Run)
    ├── main.py              # Lógica da rota, integração Gemini e envio de e-mail (SMTP)
    ├── promptia.py          # Prompt do Sistema (Engenharia de Prompt do PowerBot)
    └── requirements.txt     # Dependências da aplicação Python
```

---

## 🚀 Funcionalidades Principais

* **Triagem Inicial Obrigatória:** Solicita Nome Completo e Localização (condomínio, shopping ou estação) antes de passar instruções técnicas.
* **Diagnóstico de LEDs e Restabelecimento de Conexão:** Instrui o procedimento de reset na caixinha STECK (disjuntor DR) e avalia o comportamento do LED Amarelo (Comunicação) e Verde (Sistema).
* **Validação Rígida de Dados de Contato:** O assistente exige Telefone com DDD e E-mail/CPF antes de gerar o chamado técnico, impedindo tickets incompletos.
* **Automação de Envio por E-mail:** Intercepta a tag interna `[DISPARAR_EMAIL]` para formatar e disparar o e-mail via Gmail SMTP para `suporte@power2go.com.br` automaticamente.
* **Segurança e Isolação de Credenciais:** Arquitetura sem credenciais no front-end, protegendo as chaves da API do Gemini e do SMTP através de variáveis de ambiente no servidor.

---

## 💻 Tecnologias Utilizadas

### Front-end
* **Linguagens:** HTML5, CSS3, JavaScript (ES6+)
* **Hospedagem:** GitHub Pages
* **Comunicação:** Fetch API Assíncrona

### Back-end & Inteligência Artificial
* **Linguagem:** Python 3.11
* **Framework:** Google Functions Framework / Flask
* **Modelo LLM:** Google Gemini 3.5 Flash-Lite (Google GenAI SDK)
* **Infraestrutura Cloud:** Google Cloud Run (deploy via `--source`, usando Buildpacks + Functions Framework)
* **Serviço de Mensageria:** SMTP (Gmail App Password)

---

## 🔐 Variáveis de Ambiente

As credenciais do sistema são injetadas no ambiente de execução do Google Cloud Run e nunca sobem para o GitHub.

| Variável | Descrição |
| --- | --- |
| `GEMINI_API_KEY` | Chave de autenticação da API Google Gemini |
| `GMAIL_USER` | Conta do Gmail utilizada para o envio automático dos tickets |
| `GMAIL_APP_PASS` | Senha de aplicativo de 16 dígitos gerada no Google Conta |

---

## 🛠️ Execução do Projeto Localmente

### Pré-requisitos
* Python 3.11+ instalado
* Chave de API do Google Gemini

### 1. Clonar o repositório
```bash
git clone https://github.com/foxysprolt/web.git
cd web/OChamado
```

### 2. Configurar o Back-end
Acesse a pasta `backend` e instale as dependências:
```bash
cd backend
pip install -r requirements.txt
```

Defina as variáveis de ambiente no seu terminal:

* **Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="SUA_CHAVE_GEMINI"
$env:GMAIL_USER="seu_email@dominio.com"
$env:GMAIL_APP_PASS="sua_senha_app_16_digitos"
```

* **Linux / macOS (Bash):**
```bash
export GEMINI_API_KEY="SUA_CHAVE_GEMINI"
export GMAIL_USER="seu_email@dominio.com"
export GMAIL_APP_PASS="sua_senha_app_16_digitos"
```

Inicie o servidor local na porta `8080`:
```bash
functions-framework --target=chat_ochamado --port=8080 --debug
```

### 3. Configurar o Front-end
Para testar localmente, abra o arquivo `OChamado/index.html` usando a extensão **Live Server** no VS Code.

---

## 📦 Deploy para Produção

### Deploy do Back-end (Google Cloud Run)

O backend usa o **Functions Framework** internamente (`@functions_framework.http`), então o deploy precisa incluir um `Procfile` na pasta `backend/` apontando para o entry-point correto:

```text
web: functions-framework --target=chat_ochamado --port=$PORT
```

Com o `Procfile` e o `functions-framework` listado em `requirements.txt`, navegue até a pasta `backend` e execute:

```bash
cd backend
gcloud run deploy chat-ochamado \
  --source=. \
  --region=southamerica-east1 \
  --allow-unauthenticated
```

> ⚠️ As variáveis de ambiente (`GEMINI_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASS`) precisam estar configuradas no serviço Cloud Run — elas não são herdadas automaticamente entre revisões dependendo de como o serviço foi criado originalmente. Confira com:
> ```bash
> gcloud run services describe chat-ochamado --region=southamerica-east1 --format="value(spec.template.spec.containers[0].env)"
> ```

### Deploy do Front-end (GitHub Pages)
1. Acesse a aba **Settings** do seu repositório no GitHub.
2. Navegue até a seção **Pages** (no menu lateral esquerdo).
3. Em *Source*, selecione a opção **Deploy from a branch**.
4. Defina a branch como `main` e selecione a pasta `/OChamado` (ou `/root`, conforme sua estrutura).
5. Clique em **Save**. O site estará disponível publicamente em poucos minutos.

---

## 📝 Licença e Uso Interno

Este projeto foi desenvolvido para uso restrito e operação de suporte técnico dos pontos de recarga da **Power2Go**. Todos os direitos reservados à marca.
