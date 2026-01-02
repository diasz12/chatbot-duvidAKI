# Setup do Supabase para DuvidAKI

Este guia explica como configurar o Supabase (PostgreSQL + pgvector) para o DuvidAKI.

## Por que Supabase?

- ✅ **Grátis**: 500MB de database no free tier
- ✅ **pgvector incluído**: Suporte a vetores nativo
- ✅ **Backup automático**: Incluído no plano gratuito
- ✅ **Dashboard web**: Interface visual para gerenciar banco
- ✅ **Connection pooling**: Incluso (Supavisor)
- ✅ **Fácil setup**: 5 minutos para começar

---

## Passo 1: Criar Conta no Supabase

1. Acesse [https://supabase.com](https://supabase.com)
2. Clique em **"Start your project"**
3. Faça login com GitHub, Google ou email

---

## Passo 2: Criar Novo Projeto

1. No dashboard, clique em **"New Project"**
2. Preencha os dados:
   - **Name**: `duvidaki` (ou nome de sua preferência)
   - **Database Password**: Crie uma senha forte e **guarde-a**
   - **Region**: Escolha a mais próxima (ex: `South America (São Paulo)`)
   - **Pricing Plan**: Selecione **Free** (até 500MB)
3. Clique em **"Create new project"**
4. Aguarde 2-3 minutos enquanto o banco é provisionado

---

## Passo 3: Habilitar Extensão pgvector

1. No menu lateral, vá em **"Database" → "Extensions"**
2. Procure por **"vector"** na barra de busca
3. Clique no toggle para **habilitar a extensão pgvector**
4. Aguarde alguns segundos para ativar

> **Importante**: Sem a extensão pgvector, o vector store não funcionará!

---

## Passo 4: Obter Connection String

### Opção A: Connection String Direto (Recomendado)

1. No menu lateral, vá em **"Project Settings"** (ícone de engrenagem)
2. Clique em **"Database"**
3. Role até **"Connection string"**
4. Selecione a aba **"URI"**
5. Copie a connection string que parece com:
   ```
   postgresql://postgres.[PROJETO]:[SENHA]@aws-0-sa-east-1.pooler.supabase.com:5432/postgres
   ```
6. **Substitua `[SENHA]` pela senha que você criou no Passo 2**

### Opção B: Connection Pooling (Session Mode)

Para melhor performance com Cloud Run:

1. Na mesma página **"Database"**
2. Role até **"Connection pooling"**
3. Selecione **"Session mode"**
4. Copie a connection string com porta `6543` (não `5432`)
5. Exemplo:
   ```
   postgresql://postgres.[PROJETO]:[SENHA]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
   ```

---

## Passo 5: Configurar Variáveis de Ambiente

### No Seu `.env` Local

Crie ou edite o arquivo `.env` na raiz do projeto:

```env
# Supabase Database (copie a connection string do Passo 4)
DATABASE_URL=postgresql://postgres.XXXX:[SUA-SENHA]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres

# Resto da configuração (OpenAI, Slack, etc)
OPENAI_API_KEY=sk-proj-...
# ... outras variáveis
```

### Para Cloud Run (Deploy)

```bash
# Adicionar secret no Google Cloud
gcloud secrets create database-url \
  --data-file=- <<< "postgresql://postgres.XXXX:[SENHA]@...supabase.com:6543/postgres"

# Deploy com secret
gcloud run deploy duvidaki-bot \
  --set-secrets DATABASE_URL=database-url:latest \
  --region us-central1
```

---

## Passo 6: Testar Conexão

Execute o indexador para testar a conexão:

```bash
# Instalar dependências primeiro
pip install -r requirements.txt

# Testar indexação
python main.py index --confluence

# Ou testar query
python main.py query "Como fazer deploy?"
```

Se funcionar, você verá logs como:

```
INFO - VectorStore initialized with PostgreSQL + pgvector
INFO - Database schema initialized
INFO - Creating embeddings for 100 documents...
✅ Added 100 documents to vector store
```

---

## Passo 7: Verificar Dados no Dashboard

1. No Supabase, vá em **"Table Editor"**
2. Você deve ver a tabela **`embeddings`**
3. Clique nela para ver os documentos indexados
4. Verifique que há dados nas colunas:
   - `id`: IDs únicos
   - `document`: Textos dos documentos
   - `embedding`: Vetores (mostrado como `[...]`)
   - `metadata`: JSON com source, title, etc

---

## Troubleshooting

### Erro: "extension \"vector\" does not exist"

**Solução**: Habilite a extensão pgvector no Passo 3.

---

### Erro: "connection refused"

**Causa**: Connection string incorreta ou senha errada.

**Solução**:
1. Verifique se copiou a connection string completa
2. Confirme que substituiu `[SENHA]` pela senha real
3. Teste a conexão com `psql` ou um cliente PostgreSQL

---

### Erro: "tuple concurrently updated"

**Causa**: Multiple inserts simultâneos (raro).

**Solução**: Já tratado no código com `ON CONFLICT DO UPDATE`.

---

### Performance lenta nas buscas

**Soluções**:
1. Verifique se o índice HNSW foi criado:
   ```sql
   SELECT indexname FROM pg_indexes WHERE tablename = 'embeddings';
   ```
2. Se não houver índice, execute:
   ```sql
   CREATE INDEX embeddings_embedding_idx
   ON embeddings USING hnsw (embedding vector_cosine_ops);
   ```

---

### Limite de 500MB atingido

**Free tier do Supabase**: 500MB de storage.

**Estimativas**:
- 1 documento (1000 chars) ≈ 2-3KB com embedding
- 500MB ≈ ~150,000-200,000 documentos

**Soluções**:
1. Deletar documentos antigos/desnecessários:
   ```python
   python main.py reset
   ```
2. Filtrar apenas páginas importantes do Confluence
3. Upgrade para **Pro plan**: $25/mês (8GB incluído)

---

## Monitoramento

### Ver uso de storage

1. Dashboard Supabase → **"Settings"** → **"Usage"**
2. Verifique **"Database Size"**

### Ver queries em tempo real

1. Dashboard Supabase → **"Database"** → **"Query Performance"**
2. Analise queries lentas

### Backup

Supabase faz backup automático (free tier):
- **Daily backups**: 7 dias de retenção
- **Point-in-time recovery**: Disponível no Pro plan

---

## Custos

| Tier | Storage | Backup | Custo/mês |
|------|---------|--------|-----------|
| Free | 500MB | 7 dias | **$0** |
| Pro | 8GB | 14 dias | $25 |
| Team | 100GB | 28 dias | $599 |

**Recomendação**: Comece com Free tier. Upgrade para Pro (~R$ 150/mês) se ultrapassar 500MB.

---

## Alternativas ao Supabase

Se preferir outra opção:

| Alternativa | Free Tier | Custo Paid | Vantagem |
|-------------|-----------|------------|----------|
| **Neon** | 512MB | $19/mês | Serverless, autoscaling |
| **Railway** | $5 crédito | $10/mês | Simples, developer-friendly |
| **Render** | 90 dias | $7/mês | Inclui hosting do app |
| **Cloud SQL** | ❌ | $14/mês | Nativo GCP |

Todas suportam pgvector com a mesma implementação de código.

---

## Próximos Passos

✅ Supabase configurado
⬜ Indexar documentos do Confluence
⬜ Testar queries localmente
⬜ Deploy no Cloud Run
⬜ Configurar bot Slack

Continue em [DEPLOY.md](./DEPLOY.md) para fazer deploy no Cloud Run.
