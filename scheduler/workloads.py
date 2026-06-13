"""Ready-made and randomly generated workloads for demos and quick testing."""

from __future__ import annotations

import random
from typing import List, Optional

from .models import Process


def sample_workload() -> List[Process]:
    """A small, hand-picked workload that shows interesting scheduling behaviour."""
    return [
        Process("P1", 0, 5, 2),
        Process("P2", 1, 3, 1),
        Process("P3", 2, 8, 4),
        Process("P4", 3, 6, 3),
        Process("P5", 4, 2, 5),
    ]


def random_workload(n: int = 5, max_arrival: int = 10, max_burst: int = 10,
                     max_priority: int = 5, seed: Optional[int] = None) -> List[Process]:
    """Generate ``n`` random processes for quick experimentation."""
    rng = random.Random(seed)
    return [
        Process(
            f"P{i + 1}",
            rng.randint(0, max_arrival),
            rng.randint(1, max_burst),
            rng.randint(0, max_priority),
        )
        for i in range(n)
    ]
