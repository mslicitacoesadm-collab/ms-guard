from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


class HistoryStore:
    def __init__(self, path: str = 'data/history.json') -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text('[]', encoding='utf-8')

    def load(self) -> List[Dict]:
        try:
            return json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            return []

    def add(self, item: Dict) -> None:
        data = self.load()
        data.insert(0, item)
        data = data[:30]
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
