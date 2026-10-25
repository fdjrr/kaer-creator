import json
import sys
import argparse


def main():
    p = argparse.ArgumentParser(description="Extract Kaer API keys from JSONL/JSON." )
    p.add_argument("-i", "--input", required=True, help="input JSONL or JSON file")
    p.add_argument("-o", "--output", default="keys.txt", help="output file")
    p.add_argument("--no-dedupe", action="store_true", help="keep duplicates")
    args = p.parse_args()

    keys = []
    seen = set()
    with open(args.input) as f:
        if args.input.endswith(".jsonl"):
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                for v in obj.values():
                    if isinstance(v, str) and v.startswith("kaer_live_"):
                        if args.no_dedupe or v not in seen:
                            keys.append(v)
                            seen.add(v)
        else:
            data = json.load(f)
            if isinstance(data, list):
                for obj in data:
                    for v in obj.values():
                        if isinstance(v, str) and v.startswith("kaer_live_"):
                            if args.no_dedupe or v not in seen:
                                keys.append(v)
                                seen.add(v)
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, str) and v.startswith("kaer_live_"):
                        if args.no_dedupe or v not in seen:
                            keys.append(v)
                            seen.add(v)
    with open(args.output, "w") as f:
        for k in keys:
            f.write(k + "\n")
    print(f"{len(keys)} key(s) written to {args.output}")


if __name__ == "__main__":
    main()
