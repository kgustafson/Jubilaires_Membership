#!/usr/bin/env python3
"""Create a manifest of embedded roster images and any Word metadata."""

from __future__ import annotations

import csv
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


DEFAULT_DOCX = Path("/Users/kurtgustafson/Downloads/ChapterMembership2026.docx")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "jubilaires_membership" / "static" / "photos" / "manifest.csv"

NS = {
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def relationship_map(docx: zipfile.ZipFile) -> dict[str, str]:
    root = ET.fromstring(docx.read("word/_rels/document.xml.rels"))
    return {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in root.findall("rel:Relationship", NS)
        if rel.attrib.get("Target", "").startswith("media/")
    }


def embedded_image_rows(docx_path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(docx_path) as docx:
        rels = relationship_map(docx)
        xml = docx.read("word/document.xml").decode("utf-8", errors="replace")

    rows = []
    for match in re.finditer(r"<wp:(?:inline|anchor)\b.*?</wp:(?:inline|anchor)>", xml, flags=re.DOTALL):
        fragment = match.group(0)
        docpr_match = re.search(r"<wp:docPr\b[^>]*/>", fragment)
        descr_match = re.search(r'descr="([^"]*)"', docpr_match.group(0)) if docpr_match else None
        embed_match = re.search(r'<a:blip\b[^>]*?r:embed="([^"]+)"', fragment)
        if not embed_match:
            continue
        rel_id = embed_match.group(1)
        media_target = rels.get(rel_id, "")
        if not media_target:
            continue
        rows.append(
            {
                "position": str(len(rows) + 1),
                "relationship_id": rel_id,
                "media_file": Path(media_target).name,
                "static_path": f"/static/photos/{Path(media_target).name}",
                "description": descr_match.group(1) if descr_match and descr_match.group(1) else "",
            }
        )
    return rows


def write_manifest(rows: list[dict[str, str]], path: Path = MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["position", "relationship_id", "media_file", "static_path", "description"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    docx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DOCX
    rows = embedded_image_rows(docx_path)
    write_manifest(rows)
    described = sum(1 for row in rows if row["description"])
    print(f"Wrote {len(rows)} image references to {MANIFEST_PATH} ({described} with descriptions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
