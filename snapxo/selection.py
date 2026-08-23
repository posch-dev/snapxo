SOURCES = ("memories", "chat")
TYPES = ("photos", "videos", "voice")

# What the organizer and the scanner call these.
SOURCE_KEYS = {"memories": "memory", "chat": "chat"}


class Selection:
    # An empty list means everything on that axis, which is what no flag gives.

    def __init__(self, sources: list[str] | None = None, types: list[str] | None = None):
        self.sources = list(sources or [])
        self.types = list(types or [])

    def wants_source(self, name: str) -> bool:
        return not self.sources or name in self.sources

    def wants_type(self, name: str) -> bool:
        return not self.types or name in self.types

    @property
    def needs_voice_detection(self) -> bool:
        # Voice messages arrive as MP4 without a picture, so telling them apart
        # means opening every video. Photos alone is the one case that skips it.
        return self.wants_type("videos") or self.wants_type("voice")

    @property
    def is_everything(self) -> bool:
        return not self.sources and not self.types

    def describe(self) -> str:
        parts = []
        if self.sources:
            parts.append(" and ".join(self.sources))
        if self.types:
            parts.append(", ".join(self.types))
        return " / ".join(parts) if parts else "everything"


def parse(value: str, allowed: tuple[str, ...], flag: str) -> list[str]:
    if not value:
        return []
    picked = [part.strip().lower() for part in value.split(",") if part.strip()]
    unknown = [part for part in picked if part not in allowed]
    if unknown:
        raise ValueError(f"{flag} does not know {', '.join(unknown)}. "
                         f"Pick from: {', '.join(allowed)}")
    return [name for name in allowed if name in picked]
