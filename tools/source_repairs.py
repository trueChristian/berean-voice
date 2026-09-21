"""Explicit pre-existing HTML repairs for the one-time migration baseline.

No article wording or index metadata changes. Accessibility alt descriptions are
aligned to the already-authoritative index; original values remain in the report.
"""
from __future__ import annotations

import html
from html.parser import HTMLParser
from typing import Any
from archive import Fragment, digest, require

REPAIRS = {
    "61996151-3b49-4498-9285-995520ca542d": (
        "–Hebrews 4:9-11.</em></p>",
        "–Hebrews 4:9-11.</em></em></p>",
        "Close the already-open outer emphasis at the existing paragraph boundary; retain both existing emphasis openings and every source character.",
    ),
    "f82c479a-345a-4ffa-98d9-f10ddef90777": (
        "Grace, peace, and mercy</strong> from God",
        "Grace, peace, and mercy from God",
        "Remove an orphan closing strong tag. Do not invent bold emphasis where the existing opening tag was already closed.",
    ),
    "9b22e638-a735-48fe-b31b-817c614538ca": (
        "” (p. 29-30) [Emphasis mine.]</p>",
        "” (p. 29-30) [Emphasis mine.]",
        "Remove an orphan paragraph close inside an existing list item; no paragraph opening or wording is invented.",
    ),
}


def literal_text(text: str) -> str:
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.parts = []
        def handle_data(self, value):
            self.parts.append(value)
    parser = Text()
    parser.feed(text)
    parser.close()
    return "".join(parser.parts)


def repair_source_html(text: str, article: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    original = text
    report: dict[str, Any] = {"article_id": article["id"], "title": article["title"], "markup": [], "alt": []}
    if article["id"] in REPAIRS:
        old, new, reason = REPAIRS[article["id"]]
        require(text.count(old) == 1, f"Known repair preimage changed: {article['id']}")
        text = text.replace(old, new, 1)
        report["markup"].append({"old": old, "new": new, "reason": reason})
    parsed = Fragment(text)
    require([im["src"] for im in parsed.images] == [im["public_path"] for im in article["images"]], "Image order differs before source repairs")
    for found, expected in reversed(list(zip(parsed.images, article["images"], strict=True))):
        if found["alt"] != expected["alt"]:
            report["alt"].append({"image": found["src"], "old": found["alt"], "new": expected["alt"], "reason": "Use the existing authoritative index alt value; no new description is authored."})
            text = text[:found["alt_start"]] + html.escape(expected["alt"], quote=True) + text[found["alt_end"]:]
    report["alt"].reverse()
    require(literal_text(original) == literal_text(text), f"Source wording changed during structural repair: {article['id']}")
    if original == text:
        return text, None
    report["before_sha256"] = digest(original.encode())
    report["after_sha256"] = digest(text.encode())
    report["source_text_sha256"] = digest(literal_text(original).encode())
    report["pdf_visual_reverification_performed"] = False
    return text, report
