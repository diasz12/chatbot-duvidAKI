# Instruções para Push Manual

O código está commitado localmente, mas não consigo fazer o push devido à falta de credenciais Git no ambiente.

## Opção 1: Push Manual (Recomendado)

### No seu computador local:

```bash
# Clone o repositório
git clone https://github.com/diasz12/chatbot-duvidAKI.git
cd chatbot-duvidAKI

# Copie os arquivos do servidor para sua máquina local
# (use scp, rsync, ou baixe via interface web se disponível)

# Depois faça:
git add .
git commit -m "Initial project structure: DuvidAKI Chatbot with RAG"
git push -u origin main
```

## Opção 2: Usar Token de Acesso Pessoal

Se tiver acesso SSH ao servidor, execute:

```bash
cd /home/user/chatbot-duvidAKI

# Configure o remote com token
git remote set-url origin https://YOUR_GITHUB_TOKEN@github.com/diasz12/chatbot-duvidAKI.git

# Push
git push -u origin main
```

## Opção 3: Arquivos Disponíveis

Todos os arquivos estão em: `/home/user/chatbot-duvidAKI`

Você pode:
1. Fazer download dos arquivos
2. Criar o repositório localmente
3. Fazer o push do seu computador

## Estrutura do Projeto

```
chatbot-duvidAKI/
├── .env.example
├── .gitignore
├── README.md
├── main.py
├── requirements.txt
├── data/
├── src/
│   ├── config.py
│   ├── crawlers/
│   │   ├── confluence_crawler.py
│   │   └── github_crawler.py
│   ├── services/
│   │   ├── document_processor.py
│   │   ├── rag_service.py
│   │   └── vector_store.py
│   ├── integrations/
│   │   └── slack_bot.py
│   └── utils/
│       └── logger.py
└── tests/
```

## Commit Já Criado

Commit hash: `b998dba`
Mensagem: "Initial project structure: DuvidAKI Chatbot with RAG"

Arquivos: 20 arquivos, 2063 linhas inseridas
