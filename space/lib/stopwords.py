# space/lib/stopwords.py


def extract_keywords(text: str, min_length: int = 3) -> set[str]:
    """Extract keywords from text: tokenize, filter stopwords, strip punctuation.

    Args:
        text: Input text to extract keywords from
        min_length: Minimum keyword length (default 3)

    Returns:
        Set of normalized keywords
    """
    tokens = set(text.lower().split())
    return {t.strip(".,;:!?()[]{}") for t in tokens if len(t) > min_length and t not in stopwords}


stopwords = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "but",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "may",
    "might",
    "must",
    "can",
    "this",
    "that",
    "these",
    "those",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "as",
    "by",
    "from",
    "not",
    "all",
    "each",
    "every",
    "some",
    "any",
    "no",
    "none",
}
