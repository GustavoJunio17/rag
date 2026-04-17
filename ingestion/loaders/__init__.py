"""Interface base para todos os loaders de documentos."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractedContent:
    """Resultado da extração de um documento."""
    text: str                              # Texto extraído (para chunking)
    metadata: dict = field(default_factory=dict)  # Metadados (páginas, autor, etc.)
    file_type: str = ""

    # Apenas para Excel/CSV — indica que é dado estruturado
    is_structured: bool = False
    structured_data: Optional[list] = None  # Lista de DataFrames (um por aba)


class BaseLoader(ABC):
    """Todo loader implementa extract()."""

    @abstractmethod
    def extract(self, file_path: str) -> ExtractedContent:
        """Extrai conteúdo de um arquivo."""
        ...

    @staticmethod
    def detect_loader(file_path: str) -> "BaseLoader":
        """Factory: detecta o tipo e retorna o loader correto."""
        from .pdf_loader import PDFLoader
        from .docx_loader import DOCXLoader
        from .excel_loader import ExcelLoader
        from .txt_loader import TXTLoader

        ext = file_path.rsplit(".", 1)[-1].lower()

        loaders = {
            "pdf": PDFLoader,
            "docx": DOCXLoader,
            "doc": DOCXLoader,
            "xlsx": ExcelLoader,
            "xls": ExcelLoader,
            "csv": ExcelLoader,
            "txt": TXTLoader,
            "md": TXTLoader,
        }

        loader_class = loaders.get(ext)
        if not loader_class:
            raise ValueError(f"Tipo de arquivo não suportado: .{ext}")

        return loader_class()
