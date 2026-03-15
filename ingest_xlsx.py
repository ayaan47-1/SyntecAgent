#!/usr/bin/env python3
"""Ingest an XLSX file into the BIM classification database via the /api/ingest endpoint.

Usage:
    python ingest_xlsx.py [path/to/file.xlsx] [--url http://localhost:5001]

Defaults to the latest Coding_Classification Naming file in ./data/.
The file must be accessible to the backend container (./data/ is mounted at /app/data/).
"""
import sys
import os
import glob
import json
import argparse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description="Ingest an XLSX file into the BIM classification database.")
    parser.add_argument("file", nargs="?", help="Path to XLSX file (default: latest in ./data/)")
    parser.add_argument("--url", default="http://localhost:5001", help="Backend URL")
    parser.add_argument(
        "--container-path",
        default="/app/data",
        help="Path to the data directory inside the container (default: /app/data)",
    )
    args = parser.parse_args()

    if args.file:
        local_path = args.file
    else:
        matches = sorted(glob.glob("data/Coding_Classification*.xlsx"))
        if not matches:
            print("No Coding_Classification*.xlsx found in ./data/")
            sys.exit(1)
        local_path = matches[-1]

    if not os.path.exists(local_path):
        print(f"File not found: {local_path}")
        sys.exit(1)

    filename = os.path.basename(local_path)
    container_file_path = f"{args.container_path.rstrip('/')}/{filename}"
    url = f"{args.url.rstrip('/')}/api/ingest"

    print(f"Ingesting: {local_path}")
    print(f"Container path: {container_file_path}")
    print(f"Endpoint:  {url}")

    payload = json.dumps({"file_path": container_file_path}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            print(f"\nStatus: {resp.status} OK")
            print(f"Classifications upserted: {result.get('classifications_upserted', '?')}")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read())
        print(f"HTTP Error {e.code}: {body}")
        sys.exit(1)


if __name__ == "__main__":
    main()
