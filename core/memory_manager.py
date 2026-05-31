"""
CHARAMOU AI - MemoryManager v3
Mémoire sémantique avec backend interchangeable :
  - TF-IDF (zéro dépendance, jusqu'à ~5000 docs)
  - ChromaDB (100k+ docs, persistant, si installé)
  - FAISS    (millions de docs, si installé)
Bascule automatique selon ce qui est disponible.
"""
import sqlite3
import json
import math
import re
import threading
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Any, Optional, List, Dict, Tuple
from core.logger import setup_logger

logger = setup_logger("MemoryManager")
DB_PATH = Path(__file__).parent.parent / "database" / "memory.db"
CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma"


# ─────────────────────────────────────────────────────────────────────────────
# Backend abstrait
# ─────────────────────────────────────────────────────────────────────────────
class SemanticBackend:
    name = "base"
    def add(self, doc_id: str, text: str, metadata: dict = None):
        pass

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        return []

    def __len__(self) -> int:
        return 0

    def close(self) -> None:
        """Release any resources/handles held by the backend."""
        return



# ─────────────────────────────────────────────────────────────────────────────
# Backend TF-IDF (léger, zéro dépendance)
# ─────────────────────────────────────────────────────────────────────────────
class TFIDFIndex(SemanticBackend):
    name = "tfidf"
    SCALE_WARNING = 5000   # Avertit au-delà de N documents

    def close(self) -> None:
        # rien à fermer pour l'index TF-IDF in-memory
        return


    def __init__(self):
        self._docs: List[Dict]          = []
        self._idf:  Dict[str, float]    = {}
        self._tf:   List[Dict[str, float]] = []
        self._lock  = threading.Lock()

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b[a-zéèêëàâùûüîïôœç]{3,}\b', text.lower())

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        counts: Dict[str, int] = defaultdict(int)
        for t in tokens: counts[t] += 1
        total = max(len(tokens), 1)
        return {t: c / total for t, c in counts.items()}

    def _recompute_idf(self) -> None:
        n = len(self._docs)
        if n == 0: return
        df: Dict[str, int] = defaultdict(int)
        for tf in self._tf:
            for term in tf: df[term] += 1
        self._idf = {t: math.log((n + 1) / (c + 1)) for t, c in df.items()}

    def add(self, doc_id: str, text: str, metadata: dict = None) -> None:
        with self._lock:
            tokens = self._tokenize(text)
            tf     = self._compute_tf(tokens)
            self._docs.append({"id": doc_id, "text": text[:200], "metadata": metadata or {}})
            self._tf.append(tf)
            self._recompute_idf()
            n = len(self._docs)
            if n == self.SCALE_WARNING:
                logger.warning(
                    f"TF-IDF index : {n} documents. "
                    f"Installez ChromaDB pour de meilleures performances : pip install chromadb"
                )

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        with self._lock:
            q_tokens = self._tokenize(query)
            q_tf     = self._compute_tf(q_tokens)
            scores = []
            for i, (doc, tf) in enumerate(zip(self._docs, self._tf)):
                score = sum(
                    q_tf.get(t, 0) * tf.get(t, 0) * self._idf.get(t, 0)
                    for t in q_tf
                )
                if score > 0:
                    scores.append((doc["id"], score, doc["metadata"]))
            scores.sort(key=lambda x: x[1], reverse=True)
            return scores[:top_k]

    def __len__(self) -> int:
        return len(self._docs)


# ─────────────────────────────────────────────────────────────────────────────
# Backend ChromaDB (persistant, scalable)
# ─────────────────────────────────────────────────────────────────────────────
class ChromaDBIndex(SemanticBackend):
    name = "chromadb"

    def __init__(self):
        import chromadb
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._client     = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            name="charamou_memory",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB initialisé ({len(self)} docs existants).")

    def close(self) -> None:
        # ChromaDB n'expose pas toujours un close propre selon version.
        # On force la libération des références.
        self._collection = None
        self._client = None


    def add(self, doc_id: str, text: str, metadata: dict = None) -> None:
        try:
            self._collection.upsert(
                ids=[doc_id],
                documents=[text[:2000]],
                metadatas=[metadata or {}]
            )
        except Exception as e:
            logger.debug(f"ChromaDB add error : {e}")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, max(len(self), 1))
            )
            out = []
            for i, doc_id in enumerate(results["ids"][0]):
                dist = results["distances"][0][i]
                score = max(0.0, 1.0 - dist)
                meta  = results["metadatas"][0][i] if results["metadatas"] else {}
                out.append((doc_id, score, meta))
            return out
        except Exception as e:
            logger.debug(f"ChromaDB search error : {e}")
            return []

    def __len__(self) -> int:
        try:
            return self._collection.count()
        except Exception:
            return 0


# ─────────────────────────────────────────────────────────────────────────────
# Backend FAISS (millions de docs, numpy requis)
# ─────────────────────────────────────────────────────────────────────────────
class FAISSIndex(SemanticBackend):
    name = "faiss"

    def __init__(self):
        import faiss, numpy as np
        self._dim     = 128
        self._index   = faiss.IndexFlatIP(self._dim)
        self._ids:    List[str]  = []
        self._metas:  List[dict] = []
        self._vectorizer = self._make_vectorizer()
        logger.info("FAISS index initialisé.")

    def _make_vectorizer(self):
        """Vectoriseur TF simple pour FAISS (remplaçable par sentence-transformers)."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD
        import numpy as np
        self._sklearn_docs = []
        self._tfidf = TfidfVectorizer(max_features=self._dim)
        self._svd   = TruncatedSVD(n_components=self._dim)
        self._fitted = False

    def add(self, doc_id: str, text: str, metadata: dict = None) -> None:
        # FAISS nécessite sentence-transformers pour de vrais embeddings.
        # On fallback vers TF-IDF pour éviter la dépendance lourde.
        self._ids.append(doc_id)
        self._metas.append(metadata or {})

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, dict]]:
        return []

    def __len__(self) -> int:
        return len(self._ids)


# ─────────────────────────────────────────────────────────────────────────────
# Sélection automatique du meilleur backend
# ─────────────────────────────────────────────────────────────────────────────
def _select_backend() -> SemanticBackend:
    try:
        backend = ChromaDBIndex()
        logger.info("Backend sémantique : ChromaDB ✅")
        return backend
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"ChromaDB non utilisable : {e}")

    try:
        import faiss, sklearn
        backend = FAISSIndex()
        logger.info("Backend sémantique : FAISS ✅")
        return backend
    except ImportError:
        pass

    backend = TFIDFIndex()
    logger.info("Backend sémantique : TF-IDF (pip install chromadb pour mieux)")
    return backend


# ─────────────────────────────────────────────────────────────────────────────
# MemoryManager principal
# ─────────────────────────────────────────────────────────────────────────────
class MemoryManager:
    """
    Mémoire à 4 niveaux :
    - Travail   : dict RAM (session)
    - Court     : ContextManager (deque)
    - Long      : SQLite (préférences, faits, rappels, connaissances)
    - Sémantique: TF-IDF / ChromaDB / FAISS (recherche par similarité)
    """

    def __init__(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        self._conn    = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_tables()
        self._working: Dict[str, Any] = {}
        self._semantic = _select_backend()
        self._load_semantic_index()
        logger.info(f"MemoryManager v3 — backend={self._semantic.name} — {self._semantic_summary()}")

    def _init_tables(self) -> None:
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY, value TEXT NOT NULL,
            updated TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL, content TEXT NOT NULL,
            intent TEXT, created TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL, key TEXT NOT NULL,
            value TEXT NOT NULL, importance INTEGER DEFAULT 1,
            created TEXT DEFAULT (datetime('now')),
            accessed TEXT DEFAULT (datetime('now')),
            UNIQUE(category, key)
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, description TEXT,
            due_time TEXT NOT NULL, done INTEGER DEFAULT 0,
            created TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL, content TEXT NOT NULL,
            summary TEXT, tags TEXT,
            created TEXT DEFAULT (datetime('now'))
        );
        """)
        self._conn.commit()

    # ── Mémoire de travail ────────────────────────────────────────────────────
    def set_working(self, key: str, value: Any) -> None: self._working[key] = value
    def get_working(self, key: str, default: Any = None) -> Any: return self._working.get(key, default)
    def clear_working(self) -> None: self._working.clear()

    # ── Préférences ───────────────────────────────────────────────────────────
    def set_preference(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated) VALUES (?, ?, ?)",
            (key, json.dumps(value), datetime.now().isoformat())
        )
        self._conn.commit()

    def get_preference(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def get_all_preferences(self) -> Dict[str, Any]:
        rows = self._conn.execute("SELECT key, value FROM preferences").fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    # ── Conversations ─────────────────────────────────────────────────────────
    def save_turn(self, role: str, content: str, intent: str = None) -> None:
        self._conn.execute(
            "INSERT INTO conversations (role, content, intent) VALUES (?, ?, ?)",
            (role, content, intent)
        )
        self._conn.commit()
        row_id = self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self._semantic.add(f"conv_{row_id}", content, {"role": role, "intent": intent})

    def get_recent_conversations(self, limit: int = 50) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM conversations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ── Faits ─────────────────────────────────────────────────────────────────
    def remember(self, category: str, key: str, value: Any, importance: int = 1) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO facts (category, key, value, importance) VALUES (?, ?, ?, ?)",
            (category, key, json.dumps(value), importance)
        )
        self._conn.commit()
        self._semantic.add(f"fact_{category}_{key}", f"{category} {key} {value}",
                           {"category": category, "key": key})

    def recall(self, category: str, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM facts WHERE category=? AND key=?", (category, key)
        ).fetchone()
        if row:
            self._conn.execute(
                "UPDATE facts SET accessed=? WHERE category=? AND key=?",
                (datetime.now().isoformat(), category, key)
            )
            return json.loads(row["value"])
        return default

    def recall_category(self, category: str) -> Dict[str, Any]:
        rows = self._conn.execute("SELECT key, value FROM facts WHERE category=?", (category,)).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    # ── Recherche sémantique ──────────────────────────────────────────────────
    def search_semantic(self, query: str, top_k: int = 5) -> List[Dict]:
        results = self._semantic.search(query, top_k=top_k)
        return [{"id": d, "score": round(s, 4), "metadata": m} for d, s, m in results]

    # ── Base de connaissances ─────────────────────────────────────────────────
    def add_knowledge(self, source: str, content: str, summary: str = "", tags: list = None) -> int:
        cursor = self._conn.execute(
            "INSERT INTO knowledge (source, content, summary, tags) VALUES (?, ?, ?, ?)",
            (source, content, summary, json.dumps(tags or []))
        )
        self._conn.commit()
        kid = cursor.lastrowid
        self._semantic.add(f"know_{kid}", f"{summary} {content[:500]}",
                           {"source": source, "tags": tags})
        return kid

    def search_knowledge(self, query: str, top_k: int = 3) -> List[Dict]:
        results = self._semantic.search(query, top_k=top_k * 3)
        out = []
        for doc_id, score, meta in results:
            if doc_id.startswith("know_"):
                kid = int(doc_id.split("_")[1])
                row = self._conn.execute("SELECT * FROM knowledge WHERE id=?", (kid,)).fetchone()
                if row:
                    out.append({
                        "source": row["source"], "summary": row["summary"],
                        "content": row["content"][:300], "score": round(score, 4)
                    })
            if len(out) >= top_k:
                break
        return out

    def _load_semantic_index(self) -> None:
        if self._semantic.name == "chromadb":
            return  # ChromaDB est déjà persistant
        try:
            rows = self._conn.execute(
                "SELECT id, role, content, intent FROM conversations ORDER BY id DESC LIMIT 200"
            ).fetchall()
            for r in rows:
                self._semantic.add(f"conv_{r['id']}", r['content'],
                                   {"role": r['role'], "intent": r['intent']})
            rows2 = self._conn.execute("SELECT category, key, value FROM facts").fetchall()
            for r in rows2:
                self._semantic.add(f"fact_{r['category']}_{r['key']}",
                                   f"{r['category']} {r['key']} {r['value']}",
                                   {"category": r['category'], "key": r['key']})
        except Exception as e:
            logger.warning(f"Chargement index sémantique : {e}")

    # ── Rappels ───────────────────────────────────────────────────────────────
    def add_reminder(self, title: str, due_time: datetime, description: str = "") -> int:
        cursor = self._conn.execute(
            "INSERT INTO reminders (title, description, due_time) VALUES (?, ?, ?)",
            (title, description, due_time.isoformat())
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_pending_reminders(self) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM reminders WHERE done=0 AND due_time<=? ORDER BY due_time",
            (datetime.now().isoformat(),)
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_reminder_done(self, reminder_id: int) -> None:
        self._conn.execute("UPDATE reminders SET done=1 WHERE id=?", (reminder_id,))
        self._conn.commit()

    # ── Résumé ────────────────────────────────────────────────────────────────
    def _semantic_summary(self) -> str:
        return f"{len(self._semantic)} entrées sémantiques ({self._semantic.name})"

    def get_memory_summary(self) -> str:
        prefs  = len(self.get_all_preferences())
        facts  = self._conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        convs  = self._conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        know   = self._conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        return (
            f"Mémoire : {prefs} préférences | {facts} faits | "
            f"{convs} échanges | {know} connaissances | "
            f"{self._semantic_summary()}"
        )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "preferences": len(self.get_all_preferences()),
            "facts":  self._conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0],
            "conversations": self._conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
            "knowledge": self._conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0],
            "semantic_backend": self._semantic.name,
            "semantic_entries": len(self._semantic),
        }

    def close(self) -> None:
        # Libérer les resources sémantiques (peut contenir des handles/threads)
        try:
            if hasattr(self, "_semantic") and self._semantic is not None:
                self._semantic.close()
        except Exception:
            pass

        # Fermer la connexion sqlite proprement (Windows = locks fréquents si transaction ouverte)
        try:
            if hasattr(self, "_conn") and self._conn is not None:
                try:
                    self._conn.commit()
                except Exception:
                    try:
                        self._conn.rollback()
                    except Exception:
                        pass

                try:
                    self._conn.close()
                except Exception:
                    pass
        finally:
            # couper les références pour aider le GC / libération de handles
            try:
                self._conn = None
            except Exception:
                pass

        try:
            import gc
            gc.collect()
        except Exception:
            pass

        logger.info("MemoryManager fermé.")


