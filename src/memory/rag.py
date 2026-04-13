"""
Local RAG (Retrieval-Augmented Generation) Pipeline

Based on research:
- "Dynamic Retrieval Augmented Generation" (arXiv:2403.10081)
  — actively decides WHEN to retrieve based on LLM confidence
- "Fully local retrieval-augmented generation" (InfoWorld 2024)
  — no cloud, all embeddings computed locally

Architecture (no external dependencies beyond what's already installed):
  - Document store: SQLite (reuses existing DB)
  - Embeddings: TF-IDF style bag-of-words (no sentence-transformers needed)
  - Retrieval: BM25-inspired scoring (term frequency + inverse doc frequency)
  - Generation: Ollama with retrieved context injected into prompt
  - Dynamic retrieval: only retrieves when query contains question words
    or when Ollama confidence is low (heuristic: short/uncertain responses)

This is intentionally lightweight — no heavy ML dependencies.
For better embeddings, sentence-transformers can be swapped in later.
"""

import sqlite3
import json
import math
import re
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

log = logging.getLogger("panda.memory.rag")


@dataclass
class Document:
    """A document in the knowledge base."""
    id: Optional[int]
    title: str
    content: str
    source: str          # "user_stated" | "learned" | "system"
    tags: List[str]
    score: float = 0.0   # retrieval score (not stored)


class LocalRAG:
    """
    Local RAG pipeline using BM25-inspired retrieval + Ollama generation.

    Usage:
        rag = LocalRAG("data/panda.db")
        rag.add_document("Weather", "It's sunny today in Delhi", source="user_stated")
        answer = rag.query("What's the weather like?", ollama)
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS rag_documents (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        title    TEXT    NOT NULL,
        content  TEXT    NOT NULL,
        source   TEXT    NOT NULL DEFAULT 'user_stated',
        tags     TEXT    NOT NULL DEFAULT '[]',
        created  REAL    NOT NULL DEFAULT (unixepoch())
    );
    CREATE INDEX IF NOT EXISTS idx_rag_source ON rag_documents(source);
    """

    # BM25 parameters
    K1 = 1.5
    B  = 0.75

    def __init__(self, db_path: str = "data/panda.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._idf_cache: Dict[str, float] = {}
        self._doc_count_cache: int = 0

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(self.SCHEMA)

    # ── Write ─────────────────────────────────────────────────────────────────

    def add_document(
        self,
        title: str,
        content: str,
        source: str = "user_stated",
        tags: Optional[List[str]] = None,
    ) -> int:
        """Add a document to the knowledge base. Returns row id."""
        tags = tags or _tokenize(f"{title} {content}")
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO rag_documents (title, content, source, tags) VALUES (?,?,?,?)",
                (title, content, source, json.dumps(tags)),
            )
            self._idf_cache.clear()  # invalidate cache
            return cur.lastrowid

    def learn_from_conversation(self, user_text: str, assistant_text: str) -> None:
        """
        Extract facts from a conversation turn and store them.
        Triggered when user states preferences or facts.
        """
        FACT_PATTERNS = [
            r"i (?:prefer|like|love|enjoy|hate|dislike)\s+(.+)",
            r"my (?:name|favourite|favorite|hobby|job|work) is\s+(.+)",
            r"i (?:am|work as|study)\s+(.+)",
            r"remember (?:that\s+)?(.+)",
            r"i (?:usually|always|never|often)\s+(.+)",
        ]
        for pat in FACT_PATTERNS:
            m = re.search(pat, user_text.lower())
            if m:
                fact = m.group(1).strip().rstrip(".")
                self.add_document(
                    title=f"User preference: {fact[:40]}",
                    content=f"User stated: {user_text}",
                    source="user_stated",
                )
                log.info(f"Learned fact: {fact[:60]}")
                break

    # ── Retrieve ──────────────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 3) -> List[Document]:
        """BM25-inspired retrieval."""
        query_terms = set(_tokenize(query))
        if not query_terms:
            return []

        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM rag_documents").fetchall()

        if not rows:
            return []

        # Compute IDF if cache stale
        if len(rows) != self._doc_count_cache:
            self._build_idf(rows)
            self._doc_count_cache = len(rows)

        avg_len = sum(len(_tokenize(r["content"])) for r in rows) / len(rows)
        scored: List[Tuple[float, Document]] = []

        for row in rows:
            doc_terms = _tokenize(row["content"])
            doc_len = len(doc_terms)
            tf_map: Dict[str, int] = {}
            for t in doc_terms:
                tf_map[t] = tf_map.get(t, 0) + 1

            score = 0.0
            for term in query_terms:
                if term not in tf_map:
                    continue
                tf = tf_map[term]
                idf = self._idf_cache.get(term, 0.0)
                numerator = tf * (self.K1 + 1)
                denominator = tf + self.K1 * (1 - self.B + self.B * doc_len / max(avg_len, 1))
                score += idf * (numerator / denominator)

            if score > 0:
                doc = Document(
                    id=row["id"],
                    title=row["title"],
                    content=row["content"],
                    source=row["source"],
                    tags=json.loads(row["tags"]),
                    score=score,
                )
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def _build_idf(self, rows: list) -> None:
        """Build IDF table from all documents."""
        N = len(rows)
        df: Dict[str, int] = {}
        for row in rows:
            for term in set(_tokenize(row["content"])):
                df[term] = df.get(term, 0) + 1
        self._idf_cache = {
            term: math.log((N - freq + 0.5) / (freq + 0.5) + 1)
            for term, freq in df.items()
        }

    # ── Generate ──────────────────────────────────────────────────────────────

    def query(
        self,
        question: str,
        ollama,                    # OllamaIntegration instance
        top_k: int = 3,
        force_retrieve: bool = False,
    ) -> str:
        """
        Dynamic RAG query.

        Only retrieves context when:
        - force_retrieve=True, OR
        - question contains interrogative words (what/who/when/where/how/why)

        This follows the dynamic retrieval principle from arXiv:2403.10081.
        """
        should_retrieve = force_retrieve or _is_question(question)
        context_str = ""

        if should_retrieve:
            docs = self.retrieve(question, top_k=top_k)
            if docs:
                context_str = "\n".join(
                    f"[{d.source}] {d.title}: {d.content}" for d in docs
                )
                log.debug(f"RAG retrieved {len(docs)} docs for: {question[:50]}")

        if context_str:
            prompt = (
                f"Use the following context to answer the question.\n"
                f"Context:\n{context_str}\n\n"
                f"Question: {question}\n"
                f"Answer concisely in 1-2 sentences:"
            )
        else:
            prompt = question

        result = ollama.send_request(
            prompt=prompt,
            context="You are PANDA, a helpful AI assistant. Be concise.",
            max_tokens=200,
        )
        return result or "I'm not sure about that right now."

    def stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM rag_documents").fetchone()[0]
            by_source = conn.execute(
                "SELECT source, COUNT(*) as n FROM rag_documents GROUP BY source"
            ).fetchall()
        return {
            "total_documents": count,
            "by_source": {r["source"]: r["n"] for r in by_source},
        }


def _tokenize(text: str) -> List[str]:
    """Simple tokenizer: lowercase, remove stopwords, min length 3."""
    STOPWORDS = {
        "a","an","the","is","it","in","on","at","to","for","of","and","or",
        "but","not","with","this","that","was","are","be","been","have","has",
        "do","did","will","would","could","should","may","might","i","you",
        "he","she","we","they","me","him","her","us","them","my","your",
        "his","its","our","their","what","when","where","who","how","why",
        "can","just","so","if","then","than","as","by","from","up","about",
    }
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return [w for w in words if w not in STOPWORDS]


def _is_question(text: str) -> bool:
    """Heuristic: does this text look like a question?"""
    t = text.lower().strip()
    question_starters = ("what", "who", "when", "where", "how", "why",
                         "which", "is", "are", "do", "does", "can", "could",
                         "will", "would", "should", "tell me", "explain")
    return t.endswith("?") or any(t.startswith(s) for s in question_starters)
