# DuvidAKI

Servidor de webhooks com RAG (Confluence) e Devin AI, projetado para a arquitetura **Octo** — onde o **n8n** orquestra e roteia mensagens para tentáculos especializados via HTTP.

## Arquitetura

```
Slack → Octo Bot → n8n (orquestrador)
                      ├── POST /webhook/confluence  → DuvidAKI (RAG)
                      └── POST /webhook/devin       → DuvidAKI (Devin AI)
```

O DuvidAKI não se conecta ao Slack. Ele recebe requisições HTTP do n8n e retorna respostas JSON.

---

## Requisitos

- Python 3.11+
- PostgreSQL com pgvector (Supabase recomendado)
- Chave de API da OpenAI
- (Opcional) Credenciais do Confluence
- (Opcional) Token do Devin AI

---

## Instalacao

```bash
# 1. Clone e crie o ambiente virtual
git clone https://github.com/diasz12/chatbot-duvidAKI.git
cd chatbot-duvidAKI
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

# 2. Instale as dependencias
pip install -r requirements.txt

# 3. Configure as variaveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# 4. Inicie o servidor
uvicorn main:app --host 0.0.0.0 --port 8080
```

---

## Variaveis de ambiente

| Variavel | Obrigatoria | Descricao |
|----------|:-----------:|-----------|
| `OPENAI_API_KEY` | Sim | Chave da API OpenAI |
| `API_KEY` | Sim | Chave para autenticacao dos webhooks |
| `DATABASE_URL` | Sim | URL de conexao PostgreSQL (pgvector) |
| `CONFLUENCE_URL` | Nao | URL do Confluence |
| `CONFLUENCE_EMAIL` | Nao | Email para API do Confluence |
| `CONFLUENCE_API_TOKEN` | Nao | Token de API do Confluence |
| `CONFLUENCE_SPACE_KEY` | Nao | Chave do espaco a indexar |
| `DEVIN_API_TOKEN` | Nao | Token da API Devin AI |

Veja `.env.example` para a lista completa.

---

## Endpoints

### Healthcheck (sem autenticacao)

```
GET /health
→ {"status": "ok"}
```

### Webhooks (requerem header `X-API-Key`)

**Consulta RAG (Confluence):**

```bash
curl -X POST http://localhost:8080/webhook/confluence \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua-chave" \
  -d '{"question": "Como configurar o ambiente?"}'
```

```json
{"answer": "De acordo com a documentacao...", "status": "success"}
```

**Consulta Devin AI:**

```bash
curl -X POST http://localhost:8080/webhook/devin \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua-chave" \
  -d '{"question": "Como funciona o deploy?"}'
```

```json
{"answer": "Resposta do Devin...", "status": "success"}
```

### Administracao (requerem header `X-API-Key`)

| Metodo | Endpoint | Descricao |
|--------|----------|-----------|
| `POST` | `/index/confluence` | Dispara indexacao do Confluence |
| `GET` | `/stats` | Estatisticas da base de conhecimento |
| `POST` | `/reset` | Reseta a base de conhecimento |

---

## Autenticacao

Todos os endpoints (exceto `/health`) exigem o header `X-API-Key` com o valor configurado na variavel de ambiente `API_KEY`.

Sem o header ou com chave invalida, a resposta sera `401 Unauthorized`.

---

## Configuracao no n8n

No n8n, crie nos **HTTP Request** apontando para os webhooks:

1. **URL:** `http://<host>:8080/webhook/confluence` ou `/webhook/devin`
2. **Metodo:** POST
3. **Headers:**
   - `X-API-Key`: `<sua chave>`
   - `Content-Type`: `application/json`
4. **Body JSON:** `{ "question": "{{$json.text}}" }`

---

## Como funciona

### Indexacao (executar antes da primeira consulta)

```
Confluence → Crawler → Chunks → Embeddings (OpenAI) → PostgreSQL + pgvector
```

Dispare via endpoint:

```bash
curl -X POST http://localhost:8080/index/confluence \
  -H "X-API-Key: sua-chave"
```

### Consulta (cada requisicao ao webhook)

```
Pergunta → Embedding → Busca semantica (pgvector) → Top N docs → GPT-4 → Resposta JSON
```

---

## Estrutura do projeto

```
├── main.py                          # FastAPI app + endpoints admin
├── requirements.txt
├── .env.example
└── src/
    ├── auth.py                      # Autenticacao por API Key
    ├── config.py                    # Variaveis de ambiente
    ├── constants.py                 # Prompts e constantes
    ├── webhooks/
    │   ├── confluence_webhook.py    # POST /webhook/confluence
    │   └── devin_webhook.py         # POST /webhook/devin
    ├── services/
    │   ├── rag_service.py           # RAG (busca + geracao)
    │   ├── devin_service.py         # Cliente da API Devin
    │   ├── vector_store.py          # pgvector store
    │   └── document_processor.py    # Processamento de documentos
    ├── crawlers/
    │   └── confluence_crawler.py    # Crawler do Confluence
    ├── integrations/
    └── utils/
        ├── logger.py
        └── validators.py
```

---

## Custos estimados

| Servico | Modelo | Preco |
|---------|--------|-------|
| Embeddings | text-embedding-3-small | $0.02 / 1M tokens |
| Chat | gpt-4o-mini | $0.15 (input) / $0.60 (output) / 1M tokens |
| PostgreSQL | Supabase free tier | Gratuito ate 500MB |
