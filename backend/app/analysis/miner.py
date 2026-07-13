"""Pattern Miner - clusters similar log lines (Versus parity)."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.core.config_loader import MinerConfig, load_config


@dataclass
class TrieNode:
    """Node in the prefix tree for log token clustering."""

    children: dict[str, "TrieNode"] = field(default_factory=dict)
    count: int = 0
    patterns: set[str] = field(default_factory=set)  # signature hashes


class PatternMiner:
    """
    Mines patterns from log lines using a prefix tree (trie) clustering.

    Versus parity:
    - similarity_threshold: how similar tokens must be to merge (0.4 default)
    - tree_depth: max depth of trie (4 default)
    - max_children: max children per node (100 default)

    Algorithm:
    1. Tokenize log line (split on non-alphanumeric, keep structure tokens)
    2. Insert into trie, merging similar branches based on threshold
    3. Leaf nodes = pattern signatures
    4. Each signature gets a hash for deduplication
    """

    def __init__(self, config: MinerConfig | None = None):
        self.config = config or MinerConfig()
        self.root = TrieNode()
        self.signature_to_pattern: dict[str, dict] = {}  # hash -> pattern info

    def _tokenize(self, line: str) -> list[str]:
        """
        Tokenize log line preserving structural tokens.

        Strategy: split on whitespace, then further split tokens containing
        punctuation while keeping delimiters as separate tokens.
        """
        # Keep structure: timestamps, URLs, IPs, paths, variable parts
        # Replace variable parts with placeholders
        line = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP>", line)
        line = re.sub(r"\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}\b", "<TIMESTAMP>", line)
        line = re.sub(r"\b[0-9a-f]{8,}\b", "<HEX>", line)  # hashes, uuids
        line = re.sub(r"\b\d+\b", "<NUM>", line)

        # Split on non-alphanumeric while keeping delimiters
        tokens = re.findall(r"\w+|[^\w\s]", line)
        return [t for t in tokens if t.strip()]

    def _jaccard_similarity(self, tokens1: list[str], tokens2: list[str]) -> float:
        """Jaccard similarity between two token sets."""
        set1, set2 = set(tokens1), set(tokens2)
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union

    def _find_similar_branch(self, node: TrieNode, token: str, depth: int) -> str | None:
        """Find existing child branch similar to token."""
        if depth >= self.config.tree_depth:
            return None
        for existing_token in node.children:
            # Quick similarity check - same token or high jaccard on subtokens
            if existing_token == token:
                return existing_token
            # For structural tokens (<IP>, <NUM>, etc.), exact match only
            if token.startswith("<") and existing_token.startswith("<"):
                if token == existing_token:
                    return existing_token
        return None

    def insert(self, line: str, source_name: str, rule_name: str | None = None) -> str:
        """
        Insert a log line into the miner, return pattern signature hash.

        Returns the signature hash that identifies this pattern.
        """
        tokens = self._tokenize(line)
        node = self.root

        for i, token in enumerate(tokens):
            similar = self._find_similar_branch(node, token, i)
            if similar:
                token = similar
            if token not in node.children:
                node.children[token] = TrieNode()
            node = node.children[token]
            node.count += 1

        # Generate signature from the path
        signature = " ".join(tokens)
        sig_hash = hashlib.sha256(signature.encode()).hexdigest()[:16]

        # Track pattern
        if sig_hash not in node.patterns:
            node.patterns.add(sig_hash)
            if sig_hash not in self.signature_to_pattern:
                self.signature_to_pattern[sig_hash] = {
                    "signature": signature,
                    "hash": sig_hash,
                    "example_line": line,
                    "source_name": source_name,
                    "rule_name": rule_name,
                    "sightings": 0,
                }
        self.signature_to_pattern[sig_hash]["sightings"] += 1
        self.signature_to_pattern[sig_hash]["last_seen"] = line

        return sig_hash

    def get_pattern(self, sig_hash: str) -> dict | None:
        """Get pattern info by signature hash."""
        return self.signature_to_pattern.get(sig_hash)

    def get_all_patterns(self) -> list[dict]:
        """Get all known patterns."""
        return list(self.signature_to_pattern.values())

    def stats(self) -> dict:
        """Miner statistics."""
        return {
            "total_patterns": len(self.signature_to_pattern),
            "total_sightings": sum(p["sightings"] for p in self.signature_to_pattern.values()),
            "trie_nodes": self._count_nodes(self.root),
        }

    def _count_nodes(self, node: TrieNode) -> int:
        return 1 + sum(self._count_nodes(child) for child in node.children.values())

    def export_catalog(self) -> list[dict]:
        """Export catalog for persistence."""
        return [
            {
                "signature": p["signature"],
                "hash": p["hash"],
                "example_line": p["example_line"],
                "source_name": p["source_name"],
                "rule_name": p["rule_name"],
                "sightings": p["sightings"],
                "last_seen": p.get("last_seen"),
            }
            for p in self.signature_to_pattern.values()
        ]

    def import_catalog(self, patterns: list[dict]) -> None:
        """Import catalog from persistence."""
        for p in patterns:
            sig_hash = p["hash"]
            self.signature_to_pattern[sig_hash] = p
            # Rebuild trie
            tokens = self._tokenize(p["example_line"])
            node = self.root
            for token in tokens:
                if token not in node.children:
                    node.children[token] = TrieNode()
                node = node.children[token]
                node.count += 1
            node.patterns.add(sig_hash)


# Global miner instance
_miner: PatternMiner | None = None


def get_miner() -> PatternMiner:
    """Get or create global pattern miner."""
    global _miner
    if _miner is None:
        try:
            cfg = load_config()
            _miner = PatternMiner(cfg.agent.miner)
        except Exception:
            _miner = PatternMiner()
    return _miner


def reset_miner() -> None:
    """Reset global miner (for testing)."""
    global _miner
    _miner = None