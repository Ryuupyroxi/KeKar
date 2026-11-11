#!/usr/bin/env python3
"""Seed a KeKar data directory so the end user gets a zero-setup first run.

The build plan (D6) wants the key to be pre-provisioned so a non-technical user
never sees the first-run wizard. This writes the key into the encrypted settings
file for the target platform.

Usage:
    python tools/seed_first_run.py --data-dir /media/usb/KeKarData --key sk-...
    python tools/seed_first_run.py --data-dir ./out/KeKar_Linux/KeKarData \
        --key sk-... --model-chain "a,b,c"

Safety:
  * The key is read from the command line here so it can be piped from a secret
    store; it is never written to the repo, and never appears in a log line
    (src/logging_config.py redacts `sk-...`).
  * Refuses to run if the target already has properties, so a seeded key can
    never silently overwrite a real portfolio.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the project importable when run from anywhere.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="KeKarData directory to seed")
    parser.add_argument("--key", required=True, help="API key to store")
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--model-chain", default=None,
                        help="Comma-separated fallback model list")
    parser.add_argument("--force", action="store_true",
                        help="Seed even if the data dir already has records")
    args = parser.parse_args()

    if not args.key.startswith("sk-"):
        print("WARNING: the key does not look like an OpenRouter key "
              "(expected it to start with 'sk-').", file=sys.stderr)

    import os
    os.environ["KEKAR_DATA_DIR"] = str(args.data_dir)

    from src.config.settings import Settings
    from src.data.db import Database
    from src.data.property_repo import PropertyRepo

    args.data_dir.mkdir(parents=True, exist_ok=True)

    database = Database()
    try:
        existing = len(PropertyRepo(database.conn).list())
        if existing and not args.force:
            print(f"REFUSING: {args.data_dir} already holds {existing} "
                  f"propert{'y' if existing == 1 else 'ies'}. "
                  f"Use --force to override.")
            return 1

        settings = Settings()
        settings.api_key = args.key
        if args.api_base:
            settings.api_base = args.api_base
        if args.model_chain:
            settings.model_chain = [m.strip() for m in
                                    args.model_chain.split(",") if m.strip()]
        settings.save()
    finally:
        database.close()

    # Never echo the key back.
    masked = f"{args.key[:6]}...{args.key[-4:]}" if len(args.key) > 12 else "***"
    print(f"Seeded {args.data_dir} with key {masked}")
    print("The first-run wizard will be skipped on this drive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
