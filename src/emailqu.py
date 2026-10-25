import httpx, re, time
from loguru import logger


class EmailquClient:
    """Temp-mail client over emailqu.com REST API."""

    BASE = "https://emailqu.com"
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    def __init__(self, timeout=30):
        self._c = httpx.Client(headers={"user-agent": self.UA}, timeout=timeout)

    async def domains(self):
        r = self._c.get(f"{self.BASE}/api/domains")
        r.raise_for_status()
        return [d["domain"] for d in r.json()["domains"] if d.get("is_verified", True)]

    def emails(self, address):
        r = self._c.get(f"{self.BASE}/api/public/emails/{address}")
        return r.json().get("emails", [])

    async def wait_code(self, address, timeout=180, sender_hint="kaer"):
        """Poll inbox until a delivery appears, return the 6-digit code from the newest
        *kaer* message. Index 0 = most recent overall; we scan newest-first for a kaer
        sender subject (the domain's un-subscribed list may include other senders)."""
        deadline = time.monotonic() + timeout
        last_count = None
        while time.monotonic() < deadline:
            try:
                emails = self.emails(address)
            except Exception as e:
                logger.warning(f"inbox read error: {e}")
                emails = []
            if emails:
                for em in emails:
                    subj = em.get("subject") or ""
                    if "kaer" in (em.get("from") or "").lower() or "kaer" in subj.lower():
                        m = re.search(r"\b(\d{6})\b", subj)
                        if m:
                            return m.group(1)
            if last_count != len(emails):
                logger.info(f"waiting for mail: {len(emails)} message(s) seen, kaer code: no")
                last_count = len(emails)
            time.sleep(4)
        return None
