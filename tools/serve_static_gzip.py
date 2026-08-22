#!/usr/bin/env python3
"""
serve_static_gzip.py — server statico per misurare le performance in locale.

`python -m http.server` non va bene per i test di velocita': e' single-thread
(serializza le richieste, quindi 20 immagini diventano una coda) e non comprime.
Su una landing con ~20 risorse questo produceva ±800 ms di varianza sull'LCP tra
run identici di Lighthouse, abbastanza da nascondere l'effetto delle ottimizzazioni.

Questo server e' multi-thread e comprime con gzip, come fa Cloudflare davanti a
GoHighLevel: i numeri locali diventano confrontabili con quelli di produzione.

Uso:
    python tools/serve_static_gzip.py [--dir landing] [--port 4600]
"""

from __future__ import annotations

import argparse
import gzip
import io
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

COMPRESSIBILI = (".html", ".css", ".js", ".json", ".svg", ".txt", ".xml")


class GzipHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler + gzip per i tipi testuali."""

    protocol_version = "HTTP/1.1"

    def send_head(self):
        path = self.translate_path(self.path)
        accetta_gzip = "gzip" in self.headers.get("Accept-Encoding", "")

        if not (accetta_gzip and path.endswith(COMPRESSIBILI)):
            return super().send_head()

        try:
            raw = open(path, "rb").read()
        except OSError:
            self.send_error(404, "File not found")
            return None

        body = gzip.compress(raw, compresslevel=6)
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")  # misure sempre a freddo
        self.end_headers()
        return io.BytesIO(body)

    def log_message(self, *args):  # silenzio: sporcherebbe l'output di Lighthouse
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="landing")
    ap.add_argument("--port", type=int, default=4600)
    args = ap.parse_args()

    handler = partial(GzipHandler, directory=args.dir)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Servo {args.dir}/ su http://localhost:{args.port} (multi-thread, gzip)")
    server.serve_forever()


if __name__ == "__main__":
    main()
