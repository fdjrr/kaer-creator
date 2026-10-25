import os, json, re, time, asyncio, sys, secrets
from loguru import logger
import httpx
from dotenv import load_dotenv

try:
    from src.cli import parse_args, _env
    from src.emailqu import EmailquClient
    from src.kaer import KaerClient
    from src.proxy import ProxyPool
    from src.storage import JsonlStore
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from src.cli import parse_args, _env
    from src.emailqu import EmailquClient
    from src.kaer import KaerClient
    from src.proxy import ProxyPool
    from src.storage import JsonlStore

BANNER = """\
  ▄▄▄  ▄  ▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄
 ▐░░▌▐░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░░░▌▐░░░░░░░░░░░▌
▐░░▌▐░░░▌▐░░▀▀▀▀▀▀▀▀▀▌▐░░▀▀▀▀▀▀▀▀▀▀▀▌▐░░▀▀▀▀▀▀▀▀▀▌
▐░▌▐░▌▐░▌▐░░▌          ▐░░▌            ▐░░▌
▐░▌▐░▌▐░▌▐░░▌          ▐░░▌            ▐░░▌
▐░░▐░░▌ ▐░░▌          ▐░░▌            ▐░░▌
▐░░▐░░░▌ ▐░░▌          ▐░░▌            ▐░░▌
 ▐░░▐░░▌  ▐░░▌          ▐░░▌            ▐░░▌
 ▐░░▐░░▌   ▐░░▌          ▐░░▌            ▐░░▌
  ▐░░░░▌   ▐░░░░░░░░░░░▌ ▐░░░░░░░░░░░▌  ▐░░░░░░░░░░░░▌
   ▐░░▌     ▐░░░░░░▀░░░▌ ▐░░▀▀▀▀▀▀▀▀▀▀▌  ▐░░▀▀▀▀▀▀▀▀▀▌
    ▐▌       ▀▀▀▀▀▀▀ ▀▀▀  ▀▀▀▀▀▀▀▀▀    ▀▀▀▀▀▀▀▀▀▀▀"""

def _scorecard(stats, args):
    logger.info(f"done: {stats['created']} ok, {stats['failed']} failed")
    return 0 if stats["created"] else 1

async def create_account(index, args, pool, store, domains):
    stats = {"created": 0, "failed": 0}
    domain = secrets.choice(domains)  # random per-account
    proxy = pool.pick(index)          # round-robin by index
    proxy_show = f" via {proxy.split('@')[-1]}" if proxy and isinstance(proxy, str) and '@' in proxy else (f" via {proxy}" if proxy else "")
    try:
        kaer = KaerClient(proxy=proxy, base=args.base)
        mail = EmailquClient()

        # 1. mint temp address
        addr = f"{args.prefix}{secrets.token_hex(4)}@{domain}"
        logger.info(f"[{index+1}/{args.accounts}] address {addr}{proxy_show}")
        # 2. request code
        r = await kaer.request_code(addr)
        if r.status != 200:
            logger.warning(f"[{index+1}/{args.accounts}] code request failed: {r.json.get('message')}")
            stats["failed"] += 1
            return stats
        # 3. poll inbox
        code = await mail.wait_code(addr, timeout=args.mail_timeout)
        if not code:
            logger.warning(f"[{index+1}/{args.accounts}] no verification mail ({addr})")
            stats["failed"] += 1
            return stats
        # 4. verify
        v = await kaer.verify(addr, code)
        if not v.ok:
            logger.warning(f"[{index+1}/{args.accounts}] verify failed: {v.json.get('code')} {v.json.get('message')}")
            stats["failed"] += 1
            return stats
        # 5. mint key
        k = await kaer.create_key(f"{args.prefix}-k{index+1}")
        if not k.ok:
            logger.warning(f"[{index+1}/{args.accounts}] key mint failed: {k.json.get('message')}")
            # account exists; save record without a key
            store.append({"email": addr, "verify_status": "ok", "grant": v.json.get("grant"), "error": k.json.get("message")})
            stats["created"] += 1
            return stats
        # 6. read free credit
        acct = await kaer.account()
        free_usd = (acct.json.get("balance") or {}).get("freeCreditUsd")
        store.append({
            "email": addr,
            "key": k.json["secret"],
            "key_id": k.json.get("key", {}).get("id"),
            "grant": v.json.get("grant"),
            "grant_decision": (acct.json.get("account") or {}).get("grantDecision"),
            "free_credit_usd": free_usd,
        })
        logger.info(f"[{index+1}/{args.accounts}] created {addr} grant={v.json.get('grant')} free_credit=${free_usd}")
        stats["created"] += 1
    except Exception as e:
        logger.error(f"[{index+1}/{args.accounts}] {type(e).__name__}: {e}")
        stats["failed"] += 1
    return stats

async def run(args):
    pool = ProxyPool(args.proxy_file)
    store = JsonlStore(args.output)
    try:
        mail = EmailquClient()
        domains = await mail.domains()
    except Exception as e:
        logger.error(f"emailqu domain fetch failed: {e}")
        return _scorecard({"created": 0, "failed": args.accounts}, args)
    if not domains:
        logger.error("no verified email domains available")
        return _scorecard({"created": 0, "failed": args.accounts}, args)
    async def worker(i):
        return await create_account(i, args, pool, store, domains)
    sem = asyncio.Semaphore(args.workers)
    async def guard(i):
        async with sem:
            return await worker(i)
    results = await asyncio.gather(*[guard(i) for i in range(args.accounts)])
    stats = {"created": sum(r["created"] for r in results), "failed": sum(r["failed"] for r in results)}
    return _scorecard(stats, args)

def main():
    args = parse_args()
    load_dotenv()
    args = _env(args)
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | {message}")
    print(BANNER)
    logger.info(f"target: kaer.ai | accounts: {args.accounts} | workers: {args.workers} | output: {args.output}")
    if args.proxy_file:
        logger.info(f"proxies: {args.proxy_file}")
    try:
        code = asyncio.run(run(args))
        sys.exit(code)
    except KeyboardInterrupt:
        logger.error("interrupted")
        sys.exit(130)

if __name__ == "__main__":
    main()
