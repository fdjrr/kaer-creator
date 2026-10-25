import argparse, os

class _Defaults:
    base = "https://api.kaer.ai"
    output = "credentials.jsonl"
    accounts = 1
    workers = 1
    prefix = "kaer"
    proxy_file = None
    mail_domain = None
    mail_timeout = 180

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="kaer-creator",
        description="Kaer API (api.kaer.ai) account creator over pure HTTP: email OTP signup, free-credit grant, API key mint.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("-n", "--accounts", type=int, default=_Defaults.accounts, help="number of accounts to create")
    p.add_argument("-w", "--workers", type=int, default=_Defaults.workers, help="concurrent workers")
    p.add_argument("-o", "--output", default=_Defaults.output, help="JSONL output path")
    p.add_argument("--proxy-file", default=_Defaults.proxy_file, help="proxy pool file (one per line)")
    p.add_argument("--email-domain", dest="mail_domain", default=_Defaults.mail_domain, help="pin a specific email domain")
    p.add_argument("--prefix", default=_Defaults.prefix, help="email address prefix")
    p.add_argument("--base", default=_Defaults.base, help="API base URL")
    p.add_argument("--mail-timeout", type=int, default=_Defaults.mail_timeout, help="seconds to wait for verification mail")
    return p.parse_args(argv)

def _env(args):
    def get(name, default):
        cur = getattr(args, name, None)
        dflt = getattr(_Defaults, name, None)
        return os.environ.get(name, cur) if cur != dflt else os.environ.get(name, default)
    args.base = get("KAER_BASE", args.base)
    args.output = get("KAER_OUTPUT", args.output)
    args.proxy_file = get("KAER_PROXY_FILE", args.proxy_file)
    return args
