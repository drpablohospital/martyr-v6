"""
Manuscript Generator for Martyr v5.1
=====================================

APA 7 + PRISMA 2020 compliant manuscript builder.
Zero external dependencies — pure Python stdlib.

Submodules:
    - apa7_builder:   Full APA 7 manuscript generation (Markdown)
    - prisma_checklist: PRISMA 2020 27-item checklist (Markdown + JSON)

Usage:
    from martyr.scripts.manuscript import build_manuscript, generate_prisma_checklist

    # Build full manuscript
    md = build_manuscript(data, out_path="manuscript.md")

    # Generate PRISMA checklist
    checklist_md, checklist_json = generate_prisma_checklist(data)

Version: 5.1.0
"""

__version__ = "5.1.0"
__author__ = "Langosta (Dogma)"

# Deferred imports to avoid circular deps / unnecessary loading
from .apa7_builder import build_manuscript, APA7ManuscriptBuilder
from .generate_manuscript import PRISMAEditor, StudyCharacteristics, MetaResults

__all__ = [
    "build_manuscript",
    "APA7ManuscriptBuilder",
    "PRISMAEditor",
    "StudyCharacteristics",
    "MetaResults",
]
