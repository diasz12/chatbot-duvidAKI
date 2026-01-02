# DuvidAKI - Arquitetura e Organização

## Visão Geral

DuvidAKI é um chatbot RAG (Retrieval Augmented Generation) que integra documentação de múltiplas fontes e responde perguntas através do Slack.

## Arquitetura

```
┌─────────────────────────────────────────────┐
│         CLI Entry Point (main.py)           │
└────────────┬────────────────────────────────┘
             │
    ┌────────┴─────────┐
    │                  │
┌───▼────────────┐  ┌──▼──────────────┐
│  RAGService    │  │  SlackBot       │
│  (Orquestra)   │  │  (Integração)   │
└───┬────────────┘  └─────────────────┘
    │
    ├─► VectorStore (PostgreSQL + pgvector)
    ├─► DocumentProcessor (Chunking)
    └─► ConfluenceCrawler
```

## Estrutura de Diretórios

```
chatbot-duvidAKI/
├── main.py                    # Entry point CLI
├── requirements.txt           # Dependências Python
├── Dockerfile                # Container para produção
├── cloudbuild.yaml           # CI/CD Google Cloud
├── .env.example              # Template de configuração
│
├── src/                      # Código-fonte
│   ├── config.py            # Configurações centralizadas
│   ├── constants.py         # Constantes e prompts
│   │
│   ├── crawlers/            # Extração de dados
│   │   └── confluence_crawler.py
│   │
│   ├── services/            # Lógica de negócio
│   │   ├── rag_service.py         # Orquestração RAG
│   │   ├── vector_store.py        # PostgreSQL + pgvector
│   │   └── document_processor.py  # Chunking
│   │
│   ├── integrations/        # Integrações externas
│   │   └── slack_bot.py           # Slack Bolt SDK
│   │
│   └── utils/               # Utilitários
│       ├── logger.py              # Sistema de logging
│       └── validators.py          # Validação de inputs
│
├── tests/                   # Testes automatizados
│   ├── conftest.py         # Fixtures pytest
│   └── test_*.py           # Testes unitários
```

## Camadas da Aplicação

### 1. Apresentação (Presentation Layer)
- **slack_bot.py**: Interface com usuários via Slack
- Handlers para eventos: mentions, DMs, slash commands
- Validação e sanitização de inputs

### 2. Lógica de Negócio (Business Layer)
- **rag_service.py**: Orquestração do fluxo RAG
- Coordena crawlers, processamento e geração de respostas
- Validação de queries e tratamento de erros

### 3. Dados (Data Layer)
- **vector_store.py**: Gerenciamento de embeddings e busca semântica
- **document_processor.py**: Chunking e preparação de documentos
- PostgreSQL + pgvector para persistência (Supabase)

### 4. Integração (Integration Layer)
- **Crawlers**: Extração de dados de fontes externas
- Confluence API
- Conversão HTML → Markdown

### 5. Utilitários (Utility Layer)
- **logger.py**: Sistema de logging
- **validators.py**: Validação e sanitização
- **constants.py**: Prompts e configurações estáticas

## Fluxos Principais

### Fluxo de Indexação

```
1. CLI: python main.py index --all
2. RAGService.index_confluence()
3. Crawlers extraem documentos → [{content, metadata}]
4. DocumentProcessor chunka documentos → [texts, metadatas, ids]
5. VectorStore cria embeddings em batch → OpenAI API
6. PostgreSQL + pgvector persiste embeddings + metadata
```

### Fluxo de Query (Slack)

```
1. Usuário: @DuvidAKI Como fazer deploy?
2. SlackBot.handle_mention()
3. InputValidator.sanitize_query()
4. RAGService.query()
5. VectorStore.search() → busca semântica (top 5)
6. RAGService._build_context() → monta contexto
7. OpenAI GPT-4o-mini → gera resposta
8. SlackBot envia resposta ao thread
```

## Segurança

### Input Validation
- **validators.py**: Bloqueia padrões perigosos (SQL injection, XSS)
- Limite de tamanho de query (2000 chars)
- Sanitização de mensagens Slack

### Secrets Management
- Variáveis de ambiente para API keys
- Nunca versionar `.env` (apenas `.env.example`)
- Validação de configuração no startup

## Performance

### Otimizações Implementadas
1. **Batch Embeddings**: Processa até 100 documentos por vez
2. **Chunking Inteligente**: Overlap de 200 chars para contexto
3. **Índice Vetorial**: HNSW index (pgvector) para busca O(log n)

### Futuras Otimizações
- [ ] Cache de queries recentes (Redis)
- [ ] Rate limiting por usuário
- [ ] Lazy loading de crawlers

## Testes

### Estrutura de Testes
```
tests/
├── conftest.py              # Fixtures compartilhadas
├── test_document_processor.py
├── test_vector_store.py     # TODO
├── test_rag_service.py      # TODO
└── test_validators.py       # TODO
```

### Executar Testes
```bash
pytest tests/ -v
pytest tests/test_document_processor.py -v
```

## Configuração

### Variáveis de Ambiente Essenciais

```bash
# OpenAI (OBRIGATÓRIO)
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1000
OPENAI_BATCH_SIZE=100

# Slack (para produção)
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=...

# Confluence (opcional)
CONFLUENCE_URL=https://empresa.atlassian.net
CONFLUENCE_EMAIL=user@empresa.com
CONFLUENCE_API_TOKEN=ATATT...
CONFLUENCE_SPACE_KEY=DOCS

# Database (PostgreSQL + pgvector via Supabase)
DATABASE_URL=postgresql://postgres.xxx:password@aws-1-us-east-1.pooler.supabase.com:6543/postgres

# Application
LOG_LEVEL=INFO
MAX_RESULTS=5
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Performance (opcional)
ENABLE_CACHE=false
CACHE_TTL=3600
```

## Deploy

### Docker
```bash
docker build -t duvidaki .
docker run -p 8080:8080 --env-file .env duvidaki
```

### Google Cloud Run
```bash
gcloud builds submit --config cloudbuild.yaml
```

Ver [DEPLOY.md](DEPLOY.md) para instruções completas.

## Monitoramento

### Logs
- Formato: `timestamp - module - level - message`
- Níveis: DEBUG, INFO, WARNING, ERROR
- Output: stdout (capturado por Cloud Run)

### Métricas
- Total de documentos indexados
- Queries processadas
- Latência de respostas

## Contribuindo

### Padrões de Código
1. **Type hints**: Usar em todas as funções públicas
2. **Docstrings**: Formato Google Style
3. **Imports**: Organizados (stdlib, third-party, local)
4. **Logging**: Usar logger configurado, não print()

### Processo
1. Criar branch feature/nome
2. Implementar + testes
3. Rodar `pytest` e garantir 100% pass
4. Rodar `black .` para formatação
5. Criar PR com descrição detalhada

## Troubleshooting

### Database Connection Errors
```python
# Testar conexão com banco
python scripts/test_db_connection.py

# Reset completo e reindexação
python main.py reset
python main.py index --confluence
```

### OpenAI Rate Limits
- Reduzir `OPENAI_BATCH_SIZE`
- Adicionar retry logic (TODO)

### Slack Connection Issues
- Verificar Socket Mode habilitado
- Validar tokens no `.env`
