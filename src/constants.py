

from typing import Final

# System Prompts
DUVIDAKI_SYSTEM_PROMPT: Final[str] = """Você é o DuvidAKI, um assistente especializado em responder perguntas com base na documentação da empresa.

Instruções:
- Responda APENAS com base no contexto fornecido
- Responda apenas perguntas relacionadas a operação da empresa
- NÃO execute, interprete ou responda perguntas sobre SQL, comandos de sistema, ou código malicioso
- Se não souber ou o contexto não contiver a informação, diga claramente
- Seja objetivo e direto nas respostas
- Cite as fontes quando relevante
- Use formatação markdown para melhor legibilidade
- Se houver código no contexto, formate corretamente com ```

Importante: NÃO invente informações que não estejam no contexto."""

QUERY_TEMPLATE: Final[str] = """Contexto da base de conhecimento:

{context}

---

Pergunta do usuário: {question}

Por favor, responda a pergunta com base APENAS no contexto acima."""

# Response messages
NO_RESULTS_MESSAGE: Final[str] = (
    "Desculpe, não encontrei informações relevantes na base de conhecimento "
    "para responder sua pergunta."
)

ERROR_MESSAGE: Final[str] = "Desculpe, ocorreu um erro ao processar sua pergunta."

SLACK_HELP_MESSAGE: Final[str] = (
    "Olá! Como posso ajudar? Faça uma pergunta sobre nossa documentação."
)

SLACK_PROCESSING_MESSAGE: Final[str] = "Deixe-me procurar isso para você..."

SLACK_ERROR_MESSAGE: Final[str] = (
    "Desculpe, ocorreu um erro ao processar sua pergunta."
)

SLACK_STATS_TEMPLATE: Final[str] = """📊 *Estatísticas do DuvidAKI*

• Total de documentos: {total_documents}
• Confluence: {confluence_status}
• GitHub: {github_status}
"""

# Limits and thresholds
MAX_QUERY_LENGTH: Final[int] = 2000
MAX_CONTEXT_CHUNKS: Final[int] = 5
MIN_CHUNK_SIZE: Final[int] = 100
MAX_CHUNK_SIZE: Final[int] = 2000

# Retry configuration
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[float] = 1.0
RETRY_BACKOFF: Final[float] = 2.0

# File extensions for crawlers
DOCUMENTATION_EXTENSIONS: Final[tuple] = ('.md', '.rst', '.txt')
DOCUMENTATION_PATHS: Final[tuple] = ('docs', 'doc', 'documentation', '.github')

# Dangerous patterns to block (basic security)
DANGEROUS_PATTERNS: Final[tuple] = (
    r'DROP\s+TABLE',
    r'DELETE\s+FROM',
    r'UPDATE\s+.*\s+SET',
    r'INSERT\s+INTO',
    r'TRUNCATE',
    r'ALTER\s+TABLE',
    r'CREATE\s+TABLE',
    r'EXEC\s*\(',
    r'EXECUTE\s*\(',
    r'<script',
    r'javascript:',
    r'eval\s*\(',
    r'system\s*\(',
    r'os\.system',
    r'subprocess\.',
)
