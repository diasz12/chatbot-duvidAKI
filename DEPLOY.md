# Deploy no Google Cloud Run

Este guia explica como fazer o deploy do DuvidAKI no Google Cloud Run com Supabase (PostgreSQL + pgvector).

## ✅ Arquitetura Recomendada

- **Database**: Supabase (PostgreSQL + pgvector) - **GRÁTIS** até 500MB
- **Application**: Google Cloud Run com `min-instances=0` - **~R$ 0-50/mês**
- **Total estimado**: **R$ 0-50/mês** (dentro do free tier!)

### Por que Cloud Run + Supabase?

✅ **Custo baixo**: Grátis ou quase grátis com min-instances=0
✅ **Escalável**: Cloud Run escala automaticamente
✅ **Persistência**: Supabase mantém dados entre deploys
✅ **Backup**: Supabase faz backup automático
✅ **Simples**: Setup rápido, manutenção mínima

### Trade-off: Cold Starts

Com `min-instances=0`, o bot pode ter **2-5 segundos de delay** na primeira requisição após ficar inativo.

- ✅ **Aceitável** para chatbot corporativo (economia de ~R$ 400/mês)
- ❌ **Não aceitável** se precisar resposta instantânea 24/7

> **Dica**: Se cold starts forem um problema, use `min-instances=1` (custo extra ~R$ 400/mês)

---

## Pré-requisitos

1. **Conta Supabase** configurada ([Ver SUPABASE_SETUP.md](./SUPABASE_SETUP.md))
2. **Conta Google Cloud** com billing ativo
3. **gcloud CLI** instalado ([Download](https://cloud.google.com/sdk/docs/install))
4. **Docker** instalado (opcional para teste local)

> **IMPORTANTE**: Configure o Supabase PRIMEIRO seguindo [SUPABASE_SETUP.md](./SUPABASE_SETUP.md)

---

## Passo 1: Configurar o Google Cloud

### 1.1 Instalar gcloud CLI

Baixe e instale: https://cloud.google.com/sdk/docs/install

### 1.2 Fazer login

```bash
gcloud auth login
```

### 1.3 Criar um novo projeto (ou usar existente)

```bash
# Criar novo projeto
gcloud projects create duvidaki-bot --name="DuvidAKI Bot"

# Listar projetos existentes
gcloud projects list

# Definir projeto ativo
gcloud config set project duvidaki-bot
```

### 1.4 Ativar APIs necessárias

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 1.5 Ativar billing

Acesse: https://console.cloud.google.com/billing e associe o projeto a uma conta de pagamento.

---

## Passo 2: Configurar Secrets no Google Cloud

Vamos usar Secret Manager para armazenar credenciais de forma segura.

### 2.1 Ativar Secret Manager API

```bash
gcloud services enable secretmanager.googleapis.com
```

### 2.2 Criar Secrets

```bash
# OpenAI API Key
echo -n "sk-proj-sua-chave-openai" | gcloud secrets create openai-api-key --data-file=-

# Slack Bot Token
echo -n "xoxb-seu-slack-bot-token" | gcloud secrets create slack-bot-token --data-file=-

# Slack App Token
echo -n "xapp-seu-slack-app-token" | gcloud secrets create slack-app-token --data-file=-

# Slack Signing Secret
echo -n "seu-signing-secret" | gcloud secrets create slack-signing-secret --data-file=-

# Database URL (Supabase connection string)
echo -n "postgresql://postgres.xxx:[SENHA]@...supabase.com:6543/postgres" | \
  gcloud secrets create database-url --data-file=-

# Confluence (opcional)
echo -n "https://sua-empresa.atlassian.net" | gcloud secrets create confluence-url --data-file=-
echo -n "seu-email@empresa.com" | gcloud secrets create confluence-email --data-file=-
echo -n "seu-confluence-token" | gcloud secrets create confluence-api-token --data-file=-
```

### 2.3 Dar Permissão ao Cloud Run

```bash
# Obter o número do projeto
PROJECT_NUMBER=$(gcloud projects describe $(gcloud config get-value project) --format="value(projectNumber)")

# Dar permissão para todos os secrets
for secret in openai-api-key slack-bot-token slack-app-token slack-signing-secret database-url confluence-url confluence-email confluence-api-token; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done
```

---

## Passo 3: Deploy

### 3.1 Build da Imagem

```bash
# Build e push para Container Registry
gcloud builds submit --tag gcr.io/$(gcloud config get-value project)/duvidaki-bot
```

### 3.2 Deploy no Cloud Run

```bash
PROJECT_ID=$(gcloud config get-value project)

gcloud run deploy duvidaki-bot \
  --image gcr.io/${PROJECT_ID}/duvidaki-bot \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --cpu 1 \
  --memory 512Mi \
  --timeout 3600 \
  --min-instances 0 \
  --max-instances 5 \
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest,\
SLACK_BOT_TOKEN=slack-bot-token:latest,\
SLACK_APP_TOKEN=slack-app-token:latest,\
SLACK_SIGNING_SECRET=slack-signing-secret:latest,\
DATABASE_URL=database-url:latest,\
CONFLUENCE_URL=confluence-url:latest,\
CONFLUENCE_EMAIL=confluence-email:latest,\
CONFLUENCE_API_TOKEN=confluence-api-token:latest"
```

**Parâmetros importantes:**
- `--min-instances 0`: Economiza custo (cold starts de 2-5s)
- `--max-instances 5`: Limita escalabilidade (previne custos inesperados)
- `--timeout 3600`: 1 hora para indexação longa
- `--set-secrets`: Usa Secret Manager (mais seguro que env vars)

---

## Passo 4: Verificar Status

```bash
# Ver logs
gcloud run services logs read duvidaki-bot --region us-central1

# Listar serviços
gcloud run services list

# Descrever serviço
gcloud run services describe duvidaki-bot --region us-central1
```

---

## Passo 5: Indexar Documentos

Antes do bot funcionar, você precisa indexar sua base de conhecimento.

### 5.1 Conectar ao Cloud Run para Executar Comandos

```bash
# Obter URL do serviço
SERVICE_URL=$(gcloud run services describe duvidaki-bot --region us-central1 --format='value(status.url)')

# Executar indexação remota (via Cloud Run Jobs ou localmente)
```

### 5.2 Opção A: Indexar Localmente (Recomendado)

Mais rápido e não consome recursos do Cloud Run:

```bash
# Configurar variáveis locais
export DATABASE_URL="postgresql://postgres.xxx:SENHA@...supabase.com:6543/postgres"
export OPENAI_API_KEY="sk-proj-..."
export CONFLUENCE_URL="..."
export CONFLUENCE_EMAIL="..."
export CONFLUENCE_API_TOKEN="..."

# Instalar dependências
pip install -r requirements.txt

# Indexar
python main.py index --confluence
```

### 5.3 Opção B: Indexar via Cloud Run

Criar um Cloud Run Job para indexação:

```bash
gcloud run jobs create duvidaki-indexer \
  --image gcr.io/${PROJECT_ID}/duvidaki-bot \
  --region us-central1 \
  --set-secrets="DATABASE_URL=database-url:latest,\
OPENAI_API_KEY=openai-api-key:latest,\
CONFLUENCE_URL=confluence-url:latest,\
CONFLUENCE_EMAIL=confluence-email:latest,\
CONFLUENCE_API_TOKEN=confluence-api-token:latest" \
  --task-timeout 3600 \
  --command python \
  --args main.py,index,--confluence

# Executar indexação
gcloud run jobs execute duvidaki-indexer --region us-central1
```

---

## Custos Estimados

### Com `min-instances=0` (Configuração Recomendada)

| Item | Custo/mês (USD) | Custo/mês (BRL) |
|------|-----------------|-----------------|
| **Supabase Free Tier** | $0 | R$ 0 |
| **Cloud Run (500 req/dia)** | ~$0.05 | ~R$ 0.30 |
| **Requisições** | Grátis | Grátis |
| **OpenAI API** | ~$10-30 | ~R$ 60-180 |
| **TOTAL** | **~$10-30/mês** | **~R$ 60-180/mês** |

**Observações:**
- ✅ Supabase grátis até 500MB
- ✅ Cloud Run praticamente grátis com min-instances=0
- 💰 Principal custo: OpenAI API (queries + embeddings)

### Com `min-instances=1` (Se Precisar de Resposta Instantânea)

| Item | Custo/mês (USD) | Custo/mês (BRL) |
|------|-----------------|-----------------|
| **Supabase Free Tier** | $0 | R$ 0 |
| **Cloud Run (sempre on)** | ~$66 | ~R$ 396 |
| **OpenAI API** | ~$10-30 | ~R$ 60-180 |
| **TOTAL** | **~$76-96/mês** | **~R$ 456-576/mês** |

Para usar min-instances=1:

```bash
gcloud run services update duvidaki-bot \
  --region us-central1 \
  --min-instances 1
```

---

## Alternativa Mais Barata: Compute Engine

Se quiser economizar, considere usar uma VM pequena:

```bash
# Criar VM e2-micro (free tier elegível)
gcloud compute instances create duvidaki-bot-vm \
  --machine-type=e2-micro \
  --zone=us-central1-a \
  --image-family=debian-11 \
  --image-project=debian-cloud

# Custo: ~$6-7/mês (ou grátis no free tier)
```

---

## Troubleshooting

### Bot não inicia

Verifique os logs:
```bash
gcloud run services logs read duvidaki-bot --region us-central1 --limit 50
```

### Variáveis de ambiente não definidas

Liste as variáveis:
```bash
gcloud run services describe duvidaki-bot --region us-central1 --format export
```

Atualize:
```bash
gcloud run services update duvidaki-bot --region us-central1 --env-vars-file env.yaml
```

### ChromaDB não persiste dados

O Cloud Run limpa arquivos entre reinicializações. Você PRECISA usar storage externo (GCS, Cloud SQL, ou Pinecone).

---

## Comandos Úteis

```bash
# Deletar serviço
gcloud run services delete duvidaki-bot --region us-central1

# Ver URLs
gcloud run services list --platform managed

# Atualizar configuração
gcloud run services update duvidaki-bot --region us-central1 --memory 1Gi

# Ver custo estimado
gcloud billing accounts list
```

---

## Próximos Passos

1. ✅ Deploy básico funcionando
2. 🔄 Configurar armazenamento persistente (GCS/Cloud SQL)
3. 📊 Configurar monitoramento (Cloud Monitoring)
4. 🔔 Configurar alertas para erros
5. 🔐 Revisar permissões e segurança

---

## Precisa de Ajuda?

- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- [Pricing Calculator](https://cloud.google.com/products/calculator)
- [Cloud Run Quotas](https://cloud.google.com/run/quotas)
