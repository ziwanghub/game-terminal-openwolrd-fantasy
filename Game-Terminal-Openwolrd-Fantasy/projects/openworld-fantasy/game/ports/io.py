"""I/O port — domain/services never call print/input directly in later phases."""
from __future__ import annotations

from typing import Iterable, List, Optional, Protocol, Sequence, Union


class IO(Protocol):
    def write(self, text: str = "") -> None: ...
    def write_line(self, text: str = "") -> None: ...
    def read_line(self, prompt: str = "") -> str: ...


class TerminalIO:
    def write(self, text: str = "") -> None:
        print(text, end="")

    def write_line(self, text: str = "") -> None:
        print(text)

    def read_line(self, prompt: str = "") -> str:
        return input(prompt)


class ScriptedIO:
    """Deterministic IO for automated game tests / smoke scripts.

    Feed lines via ``inputs``. All writes are captured in ``outputs``.
    When inputs run out, raises ``EOFError`` (or returns empty if
    ``raise_on_empty=False``) so infinite field loops cannot hang CI.
    """

    def __init__(
        self,
        inputs: Optional[Sequence[str]] = None,
        *,
        raise_on_empty: bool = True,
    ) -> None:
        self._inputs: List[str] = list(inputs or [])
        self._idx = 0
        self.outputs: List[str] = []
        self.prompts: List[str] = []
        self.raise_on_empty = raise_on_empty

    def write(self, text: str = "") -> None:
        self.outputs.append(text)

    def write_line(self, text: str = "") -> None:
        self.outputs.append(text + "\n")

    def read_line(self, prompt: str = "") -> str:
        if prompt:
            self.outputs.append(prompt)
            self.prompts.append(prompt)
        if self._idx >= len(self._inputs):
            if self.raise_on_empty:
                raise EOFError(
                    f"ScriptedIO: no more inputs (prompt={prompt!r}, "
                    f"used={self._idx})"
                )
            return ""
        val = self._inputs[self._idx]
        self._idx += 1
        return val

    def push(self, *lines: str) -> None:
        """Append extra scripted answers mid-test."""
        self._inputs.extend(lines)

    def extend(self, lines: Iterable[str]) -> None:
        self._inputs.extend(lines)

    @property
    def remaining(self) -> int:
        return max(0, len(self._inputs) - self._idx)

    @property
    def consumed(self) -> int:
        return self._idx

    def joined(self) -> str:
        return "".join(self.outputs)

    def contains(self, snippet: str) -> bool:
        return snippet in self.joined()


class RichTerminalIO:
    """Optional colored output when `rich` is installed."""

    def __init__(self) -> None:
        from rich.console import Console  # type: ignore

        self._c = Console(highlight=False)

    def write(self, text: str = "") -> None:
        self._c.print(text, end="")

    def write_line(self, text: str = "") -> None:
        # mild styling for common markers
        style = None
        if text.startswith("⚔") or "ต่อสู้" in text or "BOSS" in text:
            style = "bold red"
        elif text.startswith("✔") or "สำเร็จ" in text or "LEVEL UP" in text:
            style = "bold green"
        elif text.startswith("⏸") or "หยุด" in text:
            style = "yellow"
        elif text.startswith("──") or text.startswith("==="):
            style = "cyan"
        self._c.print(text, style=style)

    def read_line(self, prompt: str = "") -> str:
        return self._c.input(prompt)


_default: Optional[Union[TerminalIO, RichTerminalIO]] = None


def get_io(prefer_rich: bool = True) -> Union[TerminalIO, RichTerminalIO]:
    global _default
    if _default is None:
        if prefer_rich:
            try:
                _default = RichTerminalIO()
            except Exception:
                _default = TerminalIO()
        else:
            _default = TerminalIO()
    return _default
