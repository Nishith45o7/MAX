"""
Hybrid BM25 + Model-Free Vector Retrieval Engine with Bi-Temporal Decay.
"""
import math
import time
import re
from typing import List, Dict, Tuple, Any
from tideline.schema import FactRecord, TIER_HALF_LIVES


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"\w+", text)]


def _ngram_vector(text: str, n: int = 3) -> Dict[str, float]:
    """Generates normalized character n-gram frequency vector for model-free fuzzy matching."""
    text = " " + text.lower().strip() + " "
    counts: Dict[str, float] = {}
    total = 0.0
    for i in range(len(text) - n + 1):
        gram = text[i:i+n]
        counts[gram] = counts.get(gram, 0.0) + 1.0
        total += 1.0
    if total > 0:
        for k in counts:
            counts[k] /= total
    return counts


def _cosine_sim(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    dot = sum(v1[k] * v2[k] for k in v1 if k in v2)
    mag1 = math.sqrt(sum(x * x for x in v1.values()))
    mag2 = math.sqrt(sum(x * x for x in v2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class HybridRetriever:
    """Computes BM25 + character vector scores combined with bi-temporal decay."""

    @classmethod
    def compute_decay(cls, record: FactRecord, now: float) -> float:
        """Calculates half-life decay factor."""
        if record.tier == "permanent":
            return 1.0
        half_life = TIER_HALF_LIVES.get(record.tier, 30 * 86400)
        age = max(0.0, now - record.updated_at)
        decay = math.exp(-0.693147 * (age / half_life))
        # Usage boost: each access slightly buffers decay
        usage_boost = 1.0 + min(0.5, record.access_count * 0.05)
        return min(1.0, decay * usage_boost)

    @classmethod
    def rank(cls, query: str, facts: List[FactRecord], top_k: int = 10) -> List[Tuple[FactRecord, float]]:
        if not facts or not query.strip():
            return []

        query_tokens = _tokenize(query)
        q_vec = _ngram_vector(query)
        now = time.time()

        # Compute IDF
        num_docs = len(facts)
        df: Dict[str, int] = {}
        doc_tokens_map = {f.id: _tokenize(f.content) for f in facts}
        doc_lens = {f.id: len(doc_tokens_map[f.id]) for f in facts}
        avg_dl = sum(doc_lens.values()) / max(1, num_docs)

        for tokens in doc_tokens_map.values():
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1

        k1 = 1.5
        b = 0.75

        scored: List[Tuple[FactRecord, float]] = []

        for fact in facts:
            # 1. BM25 Score
            tokens = doc_tokens_map[fact.id]
            doc_len = doc_lens[fact.id]
            bm25 = 0.0
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1

            for qt in query_tokens:
                if qt in tf:
                    doc_freq = df.get(qt, 1)
                    idf = math.log(1.0 + (num_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                    term_tf = tf[qt]
                    norm_tf = (term_tf * (k1 + 1.0)) / (term_tf + k1 * (1.0 - b + b * (doc_len / avg_dl)))
                    bm25 += idf * norm_tf

            # Normalize BM25 approximately into [0, 1]
            norm_bm25 = min(1.0, bm25 / max(1.0, len(query_tokens) * 2.5))

            # 2. Model-free vector recovery score
            d_vec = _ngram_vector(fact.content)
            vec_sim = _cosine_sim(q_vec, d_vec)

            # 3. Hybrid blend
            if norm_bm25 == 0.0 and vec_sim < 0.25:
                continue

            base_score = 0.7 * norm_bm25 + 0.3 * vec_sim

            # 4. Decay and Trust modulation
            decay = cls.compute_decay(fact, now)
            effective_score = base_score * decay * fact.trust_score * fact.importance

            if effective_score > 0.02:
                scored.append((fact, effective_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @classmethod
    def format_context_block(cls, ranked_facts: List[Tuple[FactRecord, float]], max_chars: int = 800) -> str:
        """Formats ranked facts into a budgeted markdown context block."""
        if not ranked_facts:
            return ""

        lines = ["[Tideline Long-Term Memory]"]
        total_len = len(lines[0])

        for fact, score in ranked_facts:
            tag = f"[{fact.segment.upper()}]"
            line = f"- {tag} {fact.content}"
            if total_len + len(line) + 1 > max_chars:
                break
            lines.append(line)
            total_len += len(line) + 1

        return "\n".join(lines)
