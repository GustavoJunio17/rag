"""
Chunking hierárquico (pai/filho) — conforme o diagrama de arquitetura.

Estratégia:
1. Divide o texto em chunks PAI (600–1200 tokens) → texto completo salvo em doc_chunks
2. Cada chunk pai é subdividido em chunks FILHO (150–300 tokens) → enviados para embedding
3. Na busca, o embedding do filho é encontrado, mas o texto do PAI é retornado ao LLM
   → Isso dá precisão na busca + contexto suficiente na resposta
"""

import uuid
from dataclasses import dataclass, field
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import config


@dataclass
class ChildChunk:
    """Chunk filho — vai para embedding."""
    id: str
    parent_id: str
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class ParentChunk:
    """Chunk pai — texto completo enviado ao LLM."""
    id: str
    content: str
    chunk_index: int
    children: list[ChildChunk] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class HierarchicalChunker:
    """Implementa chunking em dois níveis."""

    def __init__(self):
        cfg = config.chunking

        # Splitter para chunks pai (maiores)
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg.parent_chunk_size,
            chunk_overlap=cfg.parent_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

        # Splitter para chunks filho (menores, mais precisos)
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg.child_chunk_size,
            chunk_overlap=cfg.child_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def chunk(self, text: str, base_metadata: dict = None) -> list[ParentChunk]:
        """
        Divide o texto em chunks hierárquicos.

        Returns:
            Lista de ParentChunks, cada um contendo seus ChildChunks.
        """
        base_metadata = base_metadata or {}

        # 1. Divide em chunks pai
        parent_texts = self.parent_splitter.split_text(text)

        parent_chunks = []
        for idx, parent_text in enumerate(parent_texts):
            parent_id = str(uuid.uuid4())

            # 2. Subdivide cada pai em filhos
            child_texts = self.child_splitter.split_text(parent_text)

            children = []
            for child_text in child_texts:
                child = ChildChunk(
                    id=str(uuid.uuid4()),
                    parent_id=parent_id,
                    content=child_text,
                    metadata={
                        **base_metadata,
                        "parent_chunk_index": idx,
                    },
                )
                children.append(child)

            parent_chunk = ParentChunk(
                id=parent_id,
                content=parent_text,
                chunk_index=idx,
                children=children,
                metadata={
                    **base_metadata,
                    "chunk_index": idx,
                    "num_children": len(children),
                },
            )
            parent_chunks.append(parent_chunk)

        return parent_chunks
