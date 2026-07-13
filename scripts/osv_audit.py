#!/usr/bin/env python3
"""Dependency vulnerability scanner backed by the OSV database.

Usage:
    python scripts/osv_audit.py [requirements.txt]

If no requirements file is given, it is generated on the fly with
``uv export`` (run from the backend directory). Pinned versions are sent
to the OSV batch API; the process exits non-zero when any known
vulnerability is found so it can gate CI.

Note: ``uv audit`` was removed from uv (0.8+), and ``pip-audit`` needs a
resolvable virtualenv, so OSV is the reliable cross-environment path.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request

OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"
PKG_RE = re.compile(r"^([A-Za-z0-9_.\-]+)\s*==\s*([^\s;]+)")


def collect_requirements(path: str | None) -> str:
    if path:
        with open(path) as fh:
            return fh.read()
    out = subprocess.run(
        ["uv", "export", "--format=requirements.txt"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def parse_packages(text: str) -> list[tuple[str, str]]:
    pkgs: list[tuple[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-", "[")):
            continue
        m = PKG_RE.match(line)
        if m:
            pkgs.append((m.group(1), m.group(2)))
    return pkgs


def query_osv(pkgs: list[tuple[str, str]]) -> list[tuple[str, str, str, str]]:
    queries = [
        {"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in pkgs
    ]
    req = urllib.request.Request(
        OSV_BATCH_URL,
        data=json.dumps({"queries": queries}).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
    findings: list[tuple[str, str, str, str]] = []
    for (name, ver), result in zip(pkgs, resp.get("results", [])):
        for vuln in result.get("vulns", []):
            findings.append(
                (name, ver, vuln.get("id", ""), (vuln.get("summary") or "")[:90])
            )
    return findings


def main() -> int:
    req_path = sys.argv[1] if len(sys.argv) > 1 else None
    text = collect_requirements(req_path)
    pkgs = parse_packages(text)
    print(f"Scanning {len(pkgs)} pinned dependencies against OSV...", file=sys.stderr)
    findings = query_osv(pkgs)
    if not findings:
        print("No known vulnerabilities found.")
        return 0
    print(f"\nFound {len(findings)} vulnerable package(s):")
    for name, ver, vid, summary in findings:
        print(f"  - {name}=={ver}  [{vid}] {summary}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
