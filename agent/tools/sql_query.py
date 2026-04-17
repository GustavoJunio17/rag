import re
import duckdb
from core.gemini import GeminiClient
from core.prompts import SQL_GENERATOR_PROMPT
from storage.pgvector_store import PgVectorStore

def _pick_best_source(sources: list[dict], query: str) -> dict:
    """Seleciona a fonte estruturada mais relevante para a query."""
    if len(sources) == 1:
        return sources[0]

    query_lower = query.lower()
    best = None
    best_score = -1

    for source in sources:
        score = 0
        # Verifica nome do arquivo
        parquet_path = source.get("parquet_path", "").lower()
        sheet_name = (source.get("sheet_name") or "").lower()
        description = (source.get("description") or "").lower()

        # Score por palavras da query no nome do arquivo/sheet
        for word in re.findall(r'\w+', query_lower):
            if len(word) > 3:  # ignora palavras curtas
                if word in parquet_path or word in sheet_name or word in description:
                    score += 2

        # Score por colunas relevantes
        col_schema = source.get("column_schema") or {}
        for col in col_schema:
            col_lower = str(col).lower()
            for word in re.findall(r'\w+', query_lower):
                if len(word) > 3 and word in col_lower:
                    score += 1

        if score > best_score:
            best_score = score
            best = source

    return best or sources[0]


def sql_query_tool(query: str, namespace: str) -> str:
    """Executa SQL no DuckDB para responder perguntas sobre dados estruturados."""
    store = PgVectorStore()
    client = GeminiClient()

    try:
        # 1. Busca metadados das fontes estruturadas no namespace
        sources = store.get_structured_sources(namespace)
        if not sources:
            return "Nenhuma fonte de dados estruturada (Excel/CSV) encontrada para este namespace."

        # 2. Seleciona a fonte mais relevante para a query
        source = _pick_best_source(sources, query)
        schema_info = source["column_schema"]
        parquet_path = source["parquet_path"]
        sheet_name = source.get("sheet_name", "tabela")

        # 3. Gemini gera o SQL
        prompt = f"Schema: {schema_info}\nPergunta: {query}"
        sql = client.generate(prompt, system_instruction=SQL_GENERATOR_PROMPT)
        sql = sql.strip().replace("```sql", "").replace("```", "").strip()

        # 4. Substitui referência à tabela pelo caminho real do Parquet
        # O LLM pode usar o nome da sheet, 'table', 'tabela', 'df', etc.
        table_ref = f"read_parquet('{parquet_path}')"
        # Substitui padrões comuns de nome de tabela no SQL
        possible_names = [
            re.escape(sheet_name),
            r'\btable\b',
            r'\btabela\b',
            r'\bdf\b',
            r'\bdados\b',
        ]
        for pattern in possible_names:
            sql = re.sub(pattern, table_ref, sql, flags=re.IGNORECASE)

        # 5. Executa no DuckDB
        con = duckdb.connect(database=':memory:')
        try:
            result = con.execute(sql).fetchdf()
            return result.to_string()
        finally:
            con.close()

    except Exception as e:
        return f"Erro ao executar SQL: {e}"
    finally:
        store.close()
