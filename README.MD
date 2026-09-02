# 🚀 Power2Go - Support Automation Engine

Este ecossistema de automação foi projetado para transformar a gestão de suporte da **Power2Go** no Auvo Helpdesk. A arquitetura é dividida em duas ferramentas inteligentes e complementares que operam de forma autônoma para triar, responder e reduzir drasticamente a quantidade de tickets abertos na fila humana.

---

## 🏗️ Arquitetura do Sistema

```text
               +----------------------------------+
               |        CLIENTE (WhatsApp)        |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |           OChamadoBot            |  (Front-facing Chatbot)
               |  • Atendimento Inicial           |
               |  • Triagem & Coleta de Dados     |
               |  • Abertura de Ticket via API    |
               +----------------------------------+
                                |
                                v
                   +--------------------------+
                   |  AUVO HELPDESK API (v2)  |
                   +--------------------------+
                                ^
                                |
               +----------------------------------+
               |            OSChamados            |  (Backoffice Automation Engine)
               |  • Varredura Periódica (Crawler) |
               |  • Triagem & Roteamento de Fila  |
               |  • Deflexão de Chamados Simples  |
               |  • Gestão de Inatividade (Loop)  |
               +----------------------------------+

```

---

## 🤖 1. OChamado (`ochamado`) — Agente de Interface

**Objetivo:** Converter o atendimento inicial via WhatsApp em um chamado perfeitamente preenchido e estruturado na API do Auvo.

* **Triagem e Coleta:** Interage diretamente com o cliente para coletar *Nome*, *Local/Estação*, *Telefone* e *E-mail/CPF*.
* **Diagnóstico Inicial:** Aplica procedimentos rápidos de resolução (ex: Reset do DR, Teste de Chave no Veículo, Orientações de Carga).
* **Gatilho de Ticket:** Assim que valida os dados, gera o modelo estruturado de ticket com a tag `[CRIAR_TICKET_AUVO]` e insere os campos customizados (`customFields`), enviando via `POST /v2/tickets`.



---

## ⚙️ 2. OSChamados (`oschamados`) — Motor de Gestão da Fila

**Objetivo:** Roda em segundo plano (background worker) varrendo a fila do Auvo para categorizar tickets, responder dúvidas simples e encerrar chamados inativos.

### 🔄 Fluxo de Execução (Loop de Automação)

1. **Varredura da Fila (`GET /v2/tickets`):**
* Puxa periodicamente a lista de todos os tickets que estão em aberto.




2. **Análise de Interações (`GET /v2/tickets/{id}?searchInteractions=true`):**
* A IA examina cada ticket para identificar se já houve manifestação recente ou nota interna da equipe.




3. **Triagem e Classificação:**
* Caso não tenha sido triado, a IA define o **Tipo de Solicitação** (`typeId`) e a **Equipe Destino** (`teamId`) via `PATCH /v2/tickets/{id}`.




4. **Deflexão de Atendimento (Chamados Simples):**
* Para dúvidas corriqueiras, a IA envia uma resposta padrão/orientação direta ao cliente e atualiza o status para **Resolvido/Concluído**.


5. **Ciclo de Cobrança e Inatividade (Loop de 6 Horas):**
* Quando a IA precisa de mais informações do cliente, altera o status do ticket para **`Aguardando Cliente (IA)`**.
* A cada 6 horas (limite de até 4 tentativas / 24 horas), o sistema faz uma nova checagem.
* Se o cliente responder, o ticket é retornado para **Em Atendimento**.
* Se o cliente permanecer em silêncio após as 4 tentativas, o sistema envia uma mensagem final de aviso e altera o status para **Encerrado por Inatividade**.



---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.10+
* **Framework Serverless:** Google Cloud Functions (`functions_framework`)
* **Modelo de IA:** Google Gemini API (`google-genai`)
* **Plataforma de Helpdesk:** Auvo API v2 (Helpdesk, Tickets, Status e Custom Fields)


* **Gerenciamento de Ambiente:** `python-dotenv`

---

## 📌 Status de Transição Personalizados (Auvo)

Para o funcionamento correto do `oschamados`, foram mapeados os seguintes status de fluxo no painel do Auvo:

* `Novo / Em Atendimento` (ID: 99950) — Aguardando triagem da IA ou ação da equipe.


* `Aguardando Cliente (IA)` — Status dinâmico onde a IA monitora o loop de 6h.
* `Encerrado por Inatividade` — Fechamento automático por ausência de resposta do cliente.
* `Resolvido / Concluído` — Encerrado com sucesso por deflexão da IA.

## 🔮 Evolução Futura (Roadmap): IA Local / On-Premise

Como alternativa para redução de custos em escala e conformidade total com privacidade de dados (LGPD):

* **Suporte a LLMs Locais:** Implementação de conectores para modelos Open-Source (ex: Llama 3 / Mistral) rodando via **Ollama** ou **vLLM**.
* **Zero Cost per Ticket:** Eliminação do custo de API por token na varredura contínua de milhares de tickets do `oschamados`.
* **Processamento Privado:** Garantia de que dados sensíveis de clientes e condomínios permaneçam restritos ao ambiente interno da Power2Go.