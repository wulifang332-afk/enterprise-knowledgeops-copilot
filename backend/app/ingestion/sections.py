from __future__ import annotations

import re
from collections import defaultdict

from backend.app.schemas.documents import Section

from .utils import short_hash, slugify

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


class SectionParser:
    def parse(self, *, doc_id: str, content: str) -> list[Section]:
        matches = list(HEADING_RE.finditer(content))
        if not matches:
            return [
                Section(
                    section_id=f"sec:{doc_id}:document-body:01:{short_hash('document-body')}",
                    doc_id=doc_id,
                    title="Document Body",
                    heading_level=1,
                    heading_occurrence=1,
                    section_path=["Document Body"],
                    section_path_hash=short_hash("Document Body"),
                    text=content,
                    start_char=0,
                    end_char=len(content),
                )
            ]

        stack: dict[int, str] = {}
        slug_counts: dict[str, int] = defaultdict(int)
        sections: list[Section] = []

        for index, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            for stale_level in [key for key in stack if key >= level]:
                del stack[stale_level]
            stack[level] = title
            section_path = [stack[key] for key in sorted(stack)]

            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            text = content[start:end]
            if not self._has_body_text(text):
                continue

            slug = slugify(title)
            slug_counts[slug] += 1
            occurrence = slug_counts[slug]
            path_hash = short_hash(" > ".join(section_path))
            section_id = f"sec:{doc_id}:{slug}:{occurrence:02d}:{path_hash}"
            sections.append(
                Section(
                    section_id=section_id,
                    doc_id=doc_id,
                    title=title,
                    heading_level=level,
                    heading_occurrence=occurrence,
                    section_path=section_path,
                    section_path_hash=path_hash,
                    text=text,
                    start_char=start,
                    end_char=end,
                )
            )

        if not sections:
            return [
                Section(
                    section_id=f"sec:{doc_id}:document-body:01:{short_hash('document-body')}",
                    doc_id=doc_id,
                    title="Document Body",
                    heading_level=1,
                    heading_occurrence=1,
                    section_path=["Document Body"],
                    section_path_hash=short_hash("Document Body"),
                    text=content,
                    start_char=0,
                    end_char=len(content),
                )
            ]
        return sections

    @staticmethod
    def _has_body_text(section_text: str) -> bool:
        parts = section_text.split("\n", 1)
        if len(parts) == 1:
            return False
        return bool(parts[1].strip())

