import re
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationError:
    message: str


_HAS_STATE_RE = re.compile(
    r"\b(?:N\.?Y\.?|New\s+York)\b(?:\s*,?\s*\d{5}(?:-\d{4})?)?\s*$",
    re.IGNORECASE,
)


def normalize_nyc_address(raw: str) -> str | NormalizationError:
    cleaned = " ".join(raw.split()).rstrip(",").strip()

    if not cleaned:
        return NormalizationError("Please provide an address.")

    tokens = cleaned.rstrip(",").split()
    if tokens and tokens[-1].lower().rstrip(",") == "queens":
        return NormalizationError(
            "For Queens addresses, please include a neighborhood "
            "(e.g. Astoria, Ridgewood, Flushing)."
        )

    if _HAS_STATE_RE.search(cleaned):
        return cleaned

    return f"{cleaned}, New York, NY"
