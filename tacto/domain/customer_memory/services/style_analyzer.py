"""
Customer Communication Style Analyzer.

Pure domain service — no I/O, no framework dependencies.
Detects the customer's communication style from their messages
using lightweight heuristics. The detected profile is stored in
long-term memory so the AI can adapt its responses over time.
"""

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Heuristic constants
# ---------------------------------------------------------------------------

_EMOJI_PATTERN = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags
    "\U00002702-\U000027b0"
    "\U000024c2-\U0001f251"
    "\U0001f900-\U0001f9ff"  # supplemental
    "\U0001fa00-\U0001fa6f"  # chess/extended-A
    "\U0001fa70-\U0001faff"  # extended-B
    "]+",
    flags=re.UNICODE,
)

_INFORMAL_MARKERS = {
    "kkk", "kkkk", "kkkkk", "rsrs", "rsrsrs", "haha", "hahaha",
    "kk", "rs", "lol", "kkjj", "slk", "mano", "cara", "véi", "vei",
    "bro", "mlk", "moleque", "parça", "parsa", "mané", "mane",
    "tá", "ta", "né", "ne", "pô", "po", "eita", "opa", "ué", "ue",
    "show", "top", "massa", "dahora", "suave", "dboa", "de boa",
    "blz", "beleza", "valeu", "vlw", "tmj", "flw", "falou",
    "bora", "partiu", "simbora", "vamo", "vamu",
    "iai", "e ai", "e aí", "fala", "salve",
    "tbm", "tb", "pq", "vc", "vcs", "cmg", "ctg", "mt", "mto",
    "hj", "dps", "agr", "pfv", "pff", "obg", "brigado", "brigada",
}

_FORMAL_MARKERS = {
    "senhor", "senhora", "por favor", "por gentileza",
    "cordialmente", "atenciosamente", "prezado", "prezada",
    "gostaria", "poderia", "seria possível", "seria possivel",
    "agradeço", "agradeco", "obrigado", "obrigada",
    "bom dia", "boa tarde", "boa noite",
}

_POLITE_MARKERS = {
    "por favor", "por gentileza", "obrigado", "obrigada",
    "obg", "brigado", "brigada", "agradeço", "agradeco",
    "valeu", "vlw", "muito obrigado", "muito obrigada",
}

_DIRECT_INTENT_MARKERS = {
    "quero", "manda", "me vê", "me ve", "me da", "me dá",
    "bota", "coloca", "traz", "faz", "põe", "poe",
}


@dataclass(frozen=True)
class StyleProfile:
    """Immutable snapshot of a customer's communication style."""

    formality: str          # "formal" | "informal" | "neutro"
    verbosity: str          # "conciso" | "moderado" | "detalhado"
    emoji_usage: str        # "frequente" | "moderado" | "raro"
    politeness: str         # "muito educado" | "educado" | "direto"
    tone: str               # "descontraído" | "neutro" | "sério"

    def to_memory_text(self) -> str:
        """Format as a single-line text for long-term memory storage."""
        parts = [
            f"tom {self.tone}",
            f"linguagem {self.formality}",
            f"mensagens {self.verbosity}s",
        ]
        if self.emoji_usage == "frequente":
            parts.append("usa emojis com frequência")
        elif self.emoji_usage == "raro":
            parts.append("raramente usa emojis")

        if self.politeness == "muito educado":
            parts.append("muito educado e cordial")
        elif self.politeness == "direto":
            parts.append("direto e objetivo")

        return f"Perfil comunicativo: {', '.join(parts)}"


class CustomerStyleAnalyzer:
    """
    Analyzes customer messages to detect communication style.

    Uses lightweight heuristics — no LLM calls, no I/O.
    Designed to be called on every message; aggregates signals
    across multiple messages for a more accurate profile.
    """

    @classmethod
    def analyze(cls, messages: list[str]) -> StyleProfile:
        """
        Analyze one or more customer messages and return a style profile.

        Args:
            messages: List of customer message texts (most recent conversation).

        Returns:
            StyleProfile with detected communication traits.
        """
        if not messages:
            return StyleProfile(
                formality="neutro",
                verbosity="moderado",
                emoji_usage="moderado",
                politeness="educado",
                tone="neutro",
            )

        all_text = " ".join(messages)
        text_lower = all_text.lower()
        words = text_lower.split()
        total_chars = sum(len(m.strip()) for m in messages if m.strip())
        avg_length = total_chars / len(messages) if messages else 0

        formality = cls._detect_formality(text_lower, words)
        verbosity = cls._detect_verbosity(avg_length)
        emoji_usage = cls._detect_emoji_usage(all_text, messages)
        politeness = cls._detect_politeness(text_lower, words)
        tone = cls._detect_tone(formality, emoji_usage, text_lower)

        return StyleProfile(
            formality=formality,
            verbosity=verbosity,
            emoji_usage=emoji_usage,
            politeness=politeness,
            tone=tone,
        )

    @classmethod
    def analyze_single(cls, message: str) -> StyleProfile:
        """Convenience method for analyzing a single message."""
        return cls.analyze([message])

    # ------------------------------------------------------------------
    # Private heuristics
    # ------------------------------------------------------------------

    @classmethod
    def _detect_formality(cls, text_lower: str, words: list[str]) -> str:
        """Detect formality level from vocabulary signals."""
        informal_count = sum(1 for w in words if w in _INFORMAL_MARKERS)
        formal_count = sum(1 for marker in _FORMAL_MARKERS if marker in text_lower)

        if informal_count >= 2 or (informal_count >= 1 and formal_count == 0):
            return "informal"
        if formal_count >= 2 or (formal_count >= 1 and informal_count == 0):
            return "formal"
        return "neutro"

    @classmethod
    def _detect_verbosity(cls, avg_length: float) -> str:
        """Detect verbosity from average message length."""
        if avg_length < 30:
            return "conciso"
        if avg_length > 100:
            return "detalhado"
        return "moderado"

    @classmethod
    def _detect_emoji_usage(cls, all_text: str, messages: list[str]) -> str:
        """Detect emoji usage frequency."""
        emoji_count = len(_EMOJI_PATTERN.findall(all_text))
        if not messages:
            return "moderado"

        ratio = emoji_count / len(messages)
        if ratio >= 1.5:
            return "frequente"
        if ratio < 0.3:
            return "raro"
        return "moderado"

    @classmethod
    def _detect_politeness(cls, text_lower: str, words: list[str]) -> str:
        """Detect politeness level."""
        polite_count = sum(1 for marker in _POLITE_MARKERS if marker in text_lower)
        direct_count = sum(1 for w in words if w in _DIRECT_INTENT_MARKERS)

        if polite_count >= 2:
            return "muito educado"
        if direct_count >= 2 and polite_count == 0:
            return "direto"
        return "educado"

    @classmethod
    def _detect_tone(cls, formality: str, emoji_usage: str, text_lower: str) -> str:
        """Derive overall tone from other signals."""
        has_laughs = any(m in text_lower for m in ("kkk", "haha", "rsrs", "😂", "🤣"))

        if formality == "informal" or emoji_usage == "frequente" or has_laughs:
            return "descontraído"
        if formality == "formal":
            return "sério"
        return "neutro"
