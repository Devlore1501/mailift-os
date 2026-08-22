#!/usr/bin/env python3
"""
speedtest_page.py — speed test ripetibile di una pagina via Lighthouse.

Wrappa Lighthouse in CLI e stampa solo le metriche che contano, piu' la
diagnostica su cosa sta rallentando (risorse render-blocking, fasi dell'LCP,
lavoro sul main thread, peso per host). Fa N run e riporta la mediana, perche'
un singolo run di Lighthouse ha una varianza del 10-20%.

Uso:
    python tools/speedtest_page.py <url> [--runs 3] [--desktop] [--json out.json]
    python tools/speedtest_page.py <url_a> <url_b> --compare

Prerequisiti (una volta):
    mkdir -p /tmp/lhtool && cd /tmp/lhtool && npm install lighthouse

Note operative apprese misurando la landing Mailift:
  - NON usare le Performance API del browser via devtools per l'FCP: se la tab
    non e' in primo piano Chrome rimanda il primo paint e l'FCP misurato e'
    inventato (visti 1532 ms su una pagina con load a 105 ms). Lighthouse in
    headless non ha questo problema.
  - L'API PageSpeed Insights senza chiave esaurisce la quota giornaliera quasi
    subito: per iterare serve Lighthouse locale.
  - Su una pagina GoHighLevel il TTFB varia da 140 ms (cache Cloudflare calda)
    a 1,3 s (a freddo). Confronta sempre run con lo stesso stato di cache.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

LH_DIR = Path("/tmp/lhtool")
LH_BIN = LH_DIR / "node_modules" / ".bin" / "lighthouse"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

METRICS = [
    ("first-contentful-paint", "FCP"),
    ("largest-contentful-paint", "LCP"),
    ("speed-index", "Speed Index"),
    ("total-blocking-time", "TBT"),
    ("cumulative-layout-shift", "CLS"),
    ("server-response-time", "TTFB doc"),
]


def run_lighthouse(url: str, desktop: bool, out: Path) -> dict:
    if not LH_BIN.exists():
        sys.exit(f"Lighthouse non trovato in {LH_BIN}.\n"
                 f"Installa con: mkdir -p {LH_DIR} && cd {LH_DIR} && npm install lighthouse")
    cmd = [
        str(LH_BIN), url,
        "--only-categories=performance",
        "--throttling-method=simulate",
        f"--form-factor={'desktop' if desktop else 'mobile'}",
        "--output=json", f"--output-path={out}",
        "--chrome-flags=--headless=new --no-sandbox",
        "--quiet",
    ]
    if desktop:
        cmd += ["--screenEmulation.disabled", "--throttling.cpuSlowdownMultiplier=1"]
    else:
        cmd += ["--screenEmulation.mobile"]
    env_chrome = {"CHROME_PATH": CHROME} if Path(CHROME).exists() else {}
    import os
    subprocess.run(cmd, check=True, capture_output=True,
                   env={**os.environ, **env_chrome})
    return json.loads(out.read_text())


def summarize(reports: list[dict]) -> dict:
    """Mediana delle metriche numeriche su piu' run."""
    def med(key: str) -> float:
        vals = [r["audits"][key]["numericValue"] for r in reports
                if key in r["audits"] and r["audits"][key].get("numericValue") is not None]
        return statistics.median(vals) if vals else float("nan")

    scores = [r["categories"]["performance"]["score"] * 100 for r in reports]
    return {
        "score": statistics.median(scores),
        **{key: med(key) for key, _ in METRICS},
    }


def fmt(key: str, value: float) -> str:
    if key == "cumulative-layout-shift":
        return f"{value:.3f}"
    return f"{value / 1000:.2f} s" if value >= 1000 else f"{value:.0f} ms"


def print_summary(label: str, s: dict) -> None:
    print(f"\n{label}")
    print(f"  {'performance score':22s} {s['score']:.0f}/100")
    for key, name in METRICS:
        print(f"  {name:22s} {fmt(key, s[key])}")


def print_diagnostics(report: dict) -> None:
    a = report["audits"]

    def items(key):
        return a.get(key, {}).get("details", {}).get("items", [])

    rb = items("render-blocking-resources")
    if rb:
        print("\n  Risorse render-blocking:")
        for it in rb:
            print(f"    {it.get('wastedMs', 0):6.0f} ms  {it.get('url', '')[:90]}")

    lcp_phases = []
    for blk in items("largest-contentful-paint-element"):
        for row in blk.get("items", []) if isinstance(blk.get("items"), list) else []:
            if row.get("phase"):
                lcp_phases.append((row["phase"], row.get("percent"), row.get("timing")))
    if lcp_phases:
        print("\n  Composizione dell'LCP:")
        for phase, pct, timing in lcp_phases:
            t = f"{timing:.0f} ms" if isinstance(timing, (int, float)) else "-"
            print(f"    {phase:14s} {str(pct):>5s}  {t}")

    mt = items("mainthread-work-breakdown")
    if mt:
        print("\n  Lavoro sul main thread:")
        for it in sorted(mt, key=lambda x: -x.get("duration", 0))[:5]:
            print(f"    {it.get('duration', 0):6.0f} ms  {it.get('groupLabel', '')}")

    tp = items("third-party-summary")
    if tp:
        print("\n  Terze parti (peso / blocco main thread):")
        for it in sorted(tp, key=lambda x: -x.get("transferSize", 0))[:6]:
            print(f"    {it.get('transferSize', 0)/1024:7.1f} KB  "
                  f"block {it.get('blockingTime', 0):4.0f} ms  {it.get('entity', '')}")

    tw = a.get("total-byte-weight", {})
    if tw.get("displayValue"):
        print(f"\n  Peso totale: {tw['displayValue']}")


def measure(url: str, runs: int, desktop: bool) -> tuple[dict, dict]:
    reports = []
    with tempfile.TemporaryDirectory() as td:
        for i in range(runs):
            print(f"  run {i + 1}/{runs} …", end="", flush=True)
            reports.append(run_lighthouse(url, desktop, Path(td) / f"r{i}.json"))
            print(" ok")
    return summarize(reports), reports[-1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="+", help="una URL, o due con --compare")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--desktop", action="store_true")
    ap.add_argument("--compare", action="store_true",
                    help="confronta due URL e stampa il delta per metrica")
    ap.add_argument("--json", type=Path, help="salva il report Lighthouse completo")
    args = ap.parse_args()

    profile = "desktop (no throttling CPU)" if args.desktop else "mobile (4G sim, CPU 4x)"
    print(f"Profilo: {profile} — {args.runs} run per URL, riporto la mediana")

    if args.compare:
        if len(args.urls) != 2:
            sys.exit("--compare richiede esattamente due URL")
        print(f"\nA: {args.urls[0]}")
        sa, ra = measure(args.urls[0], args.runs, args.desktop)
        print(f"\nB: {args.urls[1]}")
        sb, rb = measure(args.urls[1], args.runs, args.desktop)
        print_summary("A (prima)", sa)
        print_summary("B (dopo)", sb)
        print("\nDelta B - A")
        print(f"  {'performance score':22s} {sb['score'] - sa['score']:+.0f}")
        for key, name in METRICS:
            d = sb[key] - sa[key]
            unit = "" if key == "cumulative-layout-shift" else " ms"
            print(f"  {name:22s} {d:+.3f}{unit}" if key == "cumulative-layout-shift"
                  else f"  {name:22s} {d:+.0f}{unit}")
        print("\nDiagnostica di B:")
        print_diagnostics(rb)
        if args.json:
            args.json.write_text(json.dumps(rb))
        return 0

    s, r = measure(args.urls[0], args.runs, args.desktop)
    print_summary(args.urls[0], s)
    print_diagnostics(r)
    if args.json:
        args.json.write_text(json.dumps(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
