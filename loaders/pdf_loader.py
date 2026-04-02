"""
Loader de PDF — usa PyMuPDF (fitz) para texto geral
e pdfplumber como fallback para PDFs com muitas tabelas.
"""

import fitz  # PyMuPDF
import pdfplumber
from . import BaseLoader, ExtractedContent


class PDFLoader(BaseLoader):

    def extract(self, file_path: str) -> ExtractedContent:
        """
        Estratégia:
        1. Tenta extrair com PyMuPDF (rápido, bom pra texto corrido)
        2. Se detectar muitas tabelas, usa pdfplumber pra elas
        3. Combina texto + tabelas em formato legível
        """
        text_parts = []
        metadata = {"pages": 0, "tables_found": 0}

        # --- Extração principal com PyMuPDF ---
        doc = fitz.open(file_path)
        metadata["pages"] = len(doc)
        metadata["title"] = doc.metadata.get("title", "")
        metadata["author"] = doc.metadata.get("author", "")

        for page_num, page in enumerate(doc):
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append(f"\n--- Página {page_num + 1} ---\n{page_text}")

        doc.close()

        # --- Detecção e extração de tabelas com pdfplumber ---
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table in tables:
                        metadata["tables_found"] += 1
                        table_text = self._format_table(table, page_num + 1)
                        text_parts.append(table_text)
        except Exception:
            pass  # pdfplumber falhou, segue só com PyMuPDF

        full_text = "\n".join(text_parts)

        return ExtractedContent(
            text=full_text,
            metadata=metadata,
            file_type="pdf",
        )

    @staticmethod
    def _format_table(table: list, page_num: int) -> str:
        """Converte tabela extraída em formato texto legível."""
        if not table:
            return ""

        lines = [f"\n[Tabela - Página {page_num}]"]

        # Primeira linha como cabeçalho
        headers = table[0] if table else []
        headers = [str(h or "").strip() for h in headers]
        lines.append(" | ".join(headers))
        lines.append("-" * 40)

        for row in table[1:]:
            cells = [str(c or "").strip() for c in row]
            lines.append(" | ".join(cells))

        return "\n".join(lines)
