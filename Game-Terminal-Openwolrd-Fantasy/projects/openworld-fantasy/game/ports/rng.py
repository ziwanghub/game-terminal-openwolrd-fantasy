"""RNG port for deterministic tests later."""
from __future__ import annotations

import random
from typing import Optional, Sequence, TypeVar

T = TypeVar("T")


class Rng:
    def __init__(self, seed: Optional[int] = None) -> None:
        self._r = random.Random(seed)

    def random(self) -> float:
        return self._r.random()

    def randint(self, a: int, b: int) -> int:
        return self._r.randint(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        return self._r.choice(seq)
