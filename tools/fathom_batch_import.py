#!/usr/bin/env python3
"""Importa in batch i meeting Fathom nelle cartelle clienti.

Prende un file JSON con i dati dei meeting (summary + transcript opzionale)
e crea i file call.md nei rispettivi client folder.

Usage:
    python tools/fathom_batch_import.py <meetings.json>

Il JSON deve avere la struttura:
[
  {
    "cliente": "bergamo-vini",
    "data": "2026-05-07",
    "titolo": "strategia promo maggio",
    "summary": "...",
    "transcript": "..."  // opzionale — se presente usa process_call, altrimenti summary
  },
  ...
]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

import create_call_from_summary as ccs
import process_call as pc


def main(json_path: str) -> None:
    data = json.loads(Path(json_path).read_text())
    ok, failed = 0, []

    for i, m in enumerate(data, 1):
        cliente  = m["cliente"]
        data_str = m["data"]
        titolo   = m["titolo"]
        summary  = m.get("summary", "")
        transcript = m.get("transcript", "")

        print(f"\n[{i}/{len(data)}] {cliente} | {data_str} | {titolo}")

        try:
            if transcript.strip():
                pc.run(cliente, transcript)
            elif summary.strip():
                ccs.run(cliente, data_str, titolo, summary)
            else:
                print("  ⚠ Nessun contenuto disponibile, skip")
                continue
            ok += 1
        except Exception as e:
            print(f"  ❌ {e}")
            failed.append(f"{cliente}/{data_str}: {e}")

    print(f"\n✅ {ok}/{len(data)} processati")
    if failed:
        print("Falliti:")
        for f in failed:
            print(f"  - {f}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
