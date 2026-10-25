from typing import Optional


class ProxyPool:
    """Round-robin proxy pool from a file. Deterministic base index per task so
    concurrent workers land on distinct egresses."""

    def __init__(self, path: Optional[str] = None):
        self._pools = []
        if path:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self._pools.append(line)

    def pick(self, index: int) -> Optional[str]:
        if not self._pools:
            return None
        return self._pools[index % len(self._pools)]

    def short(self) -> str:
        return "proxy"
