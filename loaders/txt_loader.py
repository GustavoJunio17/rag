"""Loader de TXT/Markdown — leitura direta."""

from . import BaseLoader, ExtractedContent


class TXTLoader(BaseLoader):

    def extract(self, file_path: str) -> ExtractedContent:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        return ExtractedContent(
            text=text,
            metadata={"char_count": len(text)},
            file_type="txt",
        )
