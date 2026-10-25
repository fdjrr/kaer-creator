import httpx
from dataclasses import dataclass
from typing import Optional


@dataclass
class Resp:
    status: int
    json: dict

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class KaerClient:
    """Pure-HTTP client for the api.kaer.ai portal + OpenAI-compatible surface.

    Auth is an email OTP over /api/apiplat/auth/*. CSRF is not required on those
    auth endpoints; the portal session cookie (`kaer_api_portal`) is the credential.
    """

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
    ORIGIN = "https://api.kaer.ai"

    def __init__(self, proxy: Optional[str] = None, base: str = "https://api.kaer.ai", timeout=60):
        headers = {"user-agent": self.UA, "origin": self.ORIGIN, "content-type": "application/json"}
        self.base = base
        self._c = httpx.Client(headers=headers, proxy=proxy, timeout=timeout)

    def _portal(self) -> "httpx.Client":
        headers = {"user-agent": self.UA, "origin": self.ORIGIN, "accept": "application/json"}
        cookies = dict(self._c.cookies)
        return httpx.Client(headers=headers, cookies=cookies)

    async def request_code(self, email: str) -> Resp:
        r = self._c.post(f"{self.base}/api/apiplat/auth/code", json={"email": email})
        return Resp(r.status_code, self._json(r))

    async def verify(self, email: str, code: str) -> Resp:
        r = self._c.post(f"{self.base}/api/apiplat/auth/verify",
                         json={"email": email, "code": code, "agreed": True})
        # capture the portal cookie set by this response
        return Resp(r.status_code, self._json(r))

    async def create_key(self, name: str) -> Resp:
        c = self._portal()
        r = c.post(f"{self.base}/api/apiplat/keys", json={"name": name})
        return Resp(r.status_code, self._json(r))

    async def account(self) -> Resp:
        c = self._portal()
        r = c.get(f"{self.base}/api/apiplat/account")
        return Resp(r.status_code, self._json(r))

    async def key_smoke(self, key: str, model: str = "deepseek-v4-flash") -> Resp:
        r = httpx.post(f"{self.base}/v1/chat/completions",
                       headers={"authorization": f"Bearer {key}", "content-type": "application/json",
                                "user-agent": self.UA},
                       json={"model": model, "messages": [{"role": "user", "content": "Say OK"}],
                             "max_tokens": 8},
                       timeout=90)
        return Resp(r.status_code, self._json(r))

    @staticmethod
    def _json(r) -> dict:
        try:
            return r.json()
        except Exception:
            return {}
