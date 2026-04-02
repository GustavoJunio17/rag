"""
Loader de Excel/CSV — tratamento especial para dados estruturados.

Estratégia (conforme o diagrama):
1. Lê o arquivo com pandas
2. Converte para Parquet (performance + compatibilidade com DuckDB)
3. Extrai schema + sample (20 linhas) para structured_sources
4. Gera também um texto resumo para indexar no RAG (opcional)
"""

import os
import pandas as pd
from pathlib import Path
from . import BaseLoader, ExtractedContent


class ExcelLoader(BaseLoader):

    SAMPLE_ROWS = 20  # Quantas linhas de amostra guardar

    def extract(self, file_path: str) -> ExtractedContent:
        ext = file_path.rsplit(".", 1)[-1].lower()

        if ext == "csv":
            sheets = {"dados": pd.read_csv(file_path)}
        else:
            # Lê todas as abas
            xls = pd.ExcelFile(file_path)
            sheets = {
                name: xls.parse(name) for name in xls.sheet_names
            }

        structured_data = []
        text_parts = []

        for sheet_name, df in sheets.items():
            # Limpa colunas sem nome
            df.columns = [
                str(c).strip() if str(c).strip() else f"coluna_{i}"
                for i, c in enumerate(df.columns)
            ]

            # Remove linhas completamente vazias
            df = df.dropna(how="all").reset_index(drop=True)

            # --- Gera o Parquet ---
            parquet_dir = Path(file_path).parent / "parquet"
            parquet_dir.mkdir(exist_ok=True)
            parquet_path = parquet_dir / f"{Path(file_path).stem}_{sheet_name}.parquet"
            df.to_parquet(str(parquet_path), index=False)

            # --- Schema ---
            schema = {
                col: str(dtype)
                for col, dtype in zip(df.columns, df.dtypes)
            }

            # --- Sample (primeiras N linhas como JSON) ---
            sample = df.head(self.SAMPLE_ROWS).to_dict(orient="records")

            # --- Estatísticas básicas ---
            stats = {}
            for col in df.select_dtypes(include=["number"]).columns:
                stats[col] = {
                    "min": float(df[col].min()) if pd.notna(df[col].min()) else None,
                    "max": float(df[col].max()) if pd.notna(df[col].max()) else None,
                    "mean": float(df[col].mean()) if pd.notna(df[col].mean()) else None,
                }

            structured_data.append({
                "sheet_name": sheet_name,
                "dataframe": df,
                "schema": schema,
                "sample": sample,
                "row_count": len(df),
                "parquet_path": str(parquet_path),
                "stats": stats,
            })

            # --- Texto resumo para indexar no RAG (opcional) ---
            text_parts.append(self._generate_text_summary(sheet_name, df, schema))

        metadata = {
            "sheets": list(sheets.keys()),
            "total_rows": sum(s["row_count"] for s in structured_data),
        }

        return ExtractedContent(
            text="\n\n".join(text_parts),
            metadata=metadata,
            file_type="xlsx" if ext != "csv" else "csv",
            is_structured=True,
            structured_data=structured_data,
        )

    @staticmethod
    def _generate_text_summary(sheet_name: str, df: pd.DataFrame, schema: dict) -> str:
        """
        Gera um resumo em texto natural da planilha.
        Isso vai pro RAG para que o LLM saiba que essa planilha existe
        e o que ela contém, sem precisar ver todos os dados.
        """
        lines = [
            f"## Planilha: {sheet_name}",
            f"Total de linhas: {len(df)}",
            f"Colunas ({len(df.columns)}): {', '.join(df.columns)}",
            f"Tipos: {', '.join(f'{k}={v}' for k, v in schema.items())}",
            "",
            "Primeiras 5 linhas de amostra:",
        ]

        # Amostra em formato tabular
        sample_text = df.head(5).to_string(index=False)
        lines.append(sample_text)

        return "\n".join(lines)
