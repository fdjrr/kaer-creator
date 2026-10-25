import json

from src.kaer import Resp
from src.emailqu import EmailquClient
from src.storage import JsonlStore
from src.proxy import ProxyPool


def test_resp_ok():
    assert Resp(200, {}).ok is True
    assert Resp(201, {}).ok is True
    assert Resp(400, {}).ok is False
    assert Resp(429, {}).ok is False


def test_proxy_pool_round_robin(tmp_path):
    f = tmp_path / "proxies.txt"
    f.write_text("http://a:p@x:1\nhttp://b:q@y:2\nhttp://c:r@z:3\n")
    p = ProxyPool(str(f))
    assert p.pick(0) == "http://a:p@x:1"
    assert p.pick(1) == "http://b:q@y:2"
    assert p.pick(4) == "http://b:q@y:2"  # wraps around
    assert ProxyPool(None).pick(0) is None


def test_store_appends(tmp_path):
    out = tmp_path / "creds.jsonl"
    s = JsonlStore(str(out))
    s.append({"email": "x@y.z", "key": "kaer_live_AAAA", "free_credit_usd": 10})
    s.append({"email": "a@b.c", "key": "kaer_live_BBBB", "free_credit_usd": 0})
    lines = [json.loads(l) for l in out.open() if l.strip()]
    assert len(lines) == 2
    assert lines[0]["key"] == "kaer_live_AAAA"
    assert lines[1]["free_credit_usd"] == 0


def test_emailqu_ua():
    m = EmailquClient()
    assert m._c.headers["user-agent"].startswith("Mozilla/5.0")
