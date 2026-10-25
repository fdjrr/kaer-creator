import json, os, tempfile


class JsonlStore:
    """Append-only JSONL credential store. One record per account, minimal schema:
    email, key, grant, free_credit_usd. Written the moment the credential exists."""

    def __init__(self, path: str):
        self.path = path

    def append(self, record: dict) -> None:
        dirn = os.path.dirname(os.path.abspath(self.path)) or "."
        os.makedirs(dirn, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")
