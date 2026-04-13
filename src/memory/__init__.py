"""
Memory and knowledge management components.

Research foundations:
- Episodic memory with temporal decay (arXiv:2512.13564, arXiv:2502.16090)
- Thermodynamic decay model (arXiv:2602.21220)
- Dynamic RAG retrieval (arXiv:2403.10081)
- Local-first design (no cloud transmission)
"""

from .episodic import EpisodicMemory, Episode
from .rag import LocalRAG, Document

__all__ = ["EpisodicMemory", "Episode", "LocalRAG", "Document"]
