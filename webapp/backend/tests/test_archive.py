"""Test dell'archivio con Gmail e Drive finti (nessuna chiamata di rete)."""
import os
import tempfile
from datetime import datetime, timezone

os.environ["WEBAPP_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ARCHIVE_ROOT_FOLDER_ID"] = "ROOT"

import pytest  # noqa: E402

from app.db import SessionLocal, init_db  # noqa: E402
from app.models.db_models import ArchivedFile  # noqa: E402
from app.services import archive  # noqa: E402


class FakeGmail:
    def __init__(self, messages):
        self.messages = messages  # id -> (meta, {att_id: bytes})

    def search(self, q, max_results=300):
        return list(self.messages)

    def get(self, mid):
        meta, atts = self.messages[mid]
        return {**meta, "id": mid, "pdfs": [{"filename": f, "attachment_id": a} for a, f in
                                              [(k, v[0]) for k, v in atts.items()]]}

    def download(self, mid, att):
        return self.messages[mid][1][att][1]


class FakeDrive:
    def __init__(self):
        self.folders, self.files = {}, {}

    def ensure_folder(self, name, parent):
        return self.folders.setdefault((parent, name), f"{parent}/{name}")

    def ensure_path(self, parts, root):
        for p in parts:
            root = self.ensure_folder(p, root)
        return root

    def find(self, name, parent):
        return self.files.get((parent, name), {}).get("id")

    def upload_pdf(self, name, data, parent):
        fid = f"f{len(self.files)}"
        self.files[(parent, name)] = {"id": fid, "data": data}
        return fid, f"https://drive/{fid}"


def msg(sender, subject, fname, data, day=5, month=11):
    return ({"from": sender, "subject": subject, "snippet": "",
             "date": datetime(2026, month, day, 10, tzinfo=timezone.utc)},
            {"a1": (fname, data)})


@pytest.fixture(autouse=True)
def fresh_db():
    init_db()
    from app.db import Base, engine
    Base.metadata.drop_all(engine)
    init_db()


def run(gmail_msgs, drive, dry=False, business_msgs=None):
    g = {"personal": FakeGmail(gmail_msgs), "business": FakeGmail(business_msgs or {})}
    return archive.run_archive(dry_run=dry, gmail_factory=lambda a: g[a], drive_factory=lambda a: drive)


def test_upload_folder_and_dedupe():
    d = FakeDrive()
    m = {"m1": msg("billing@mail.openai.com", "Your receipt", "Receipt-1.pdf", b"%PDF-1"),
         "m2": msg("news@shop.it", "Offerte", "promo.pdf", b"%PDF-2")}
    s = run(m, d)
    assert s["accounts"]["personal"]["uploaded"] == 1
    assert s["accounts"]["personal"]["not_invoice"] == 1
    assert ("ROOT/2026/11/Openai", "2026-11-05 Receipt-1.pdf") in d.files
    # secondo giro: email gia' viste, nessun upload
    s2 = run(m, d)
    assert s2["accounts"]["personal"]["already_seen"] == 2
    assert len(d.files) == 1
    # stesso PDF in un'altra email: duplicato per hash
    m3 = {"m9": msg("billing@openai.com", "Receipt again", "copy.pdf", b"%PDF-1")}
    s3 = run(m3, d)
    assert s3["accounts"]["personal"]["duplicates"] == 1
    assert len(d.files) == 1


def test_dry_run_writes_nothing():
    d = FakeDrive()
    m = {"m1": msg("a@stripe.com", "Invoice 12", "inv.pdf", b"%PDF-3")}
    s = run(m, d, dry=True)
    assert s["items"][0]["action"] == "would_upload"
    assert not d.files
    with SessionLocal() as db:
        assert db.query(ArchivedFile).count() == 0
    # in dry-run le email non vengono segnate come viste
    assert run(m, d, dry=True)["accounts"]["personal"]["already_seen"] == 0


def test_revolut_statement_named_and_month_checked(monkeypatch):
    monkeypatch.setattr(archive, "detect_statement_period", lambda pdf, dt: "2026-10")
    d = FakeDrive()
    b = {"r1": msg("no-reply@revolut.com", "Your October statement", "stmt.pdf", b"%PDF-R1", month=11)}
    s = run({}, d, business_msgs=b)
    folder = archive.accountant_folder_id()
    assert s["accounts"]["business"]["revolut_uploaded"] == 1
    assert (folder, "Revolut 2026-10.pdf") in d.files
    # stesso mese, PDF diverso: non si carica un secondo file
    b2 = {"r2": msg("no-reply@revolut.com", "Statement October (reissued)", "s2.pdf", b"%PDF-R2")}
    s2 = run({}, d, business_msgs=b2)
    assert s2["accounts"]["business"]["revolut_existing"] == 1
    assert len([k for k in d.files if k[0] == folder]) == 1


def test_revolut_existing_in_drive_is_not_overwritten(monkeypatch):
    monkeypatch.setattr(archive, "detect_statement_period", lambda pdf, dt: "2026-09")
    d = FakeDrive()
    d.files[(archive.accountant_folder_id(), "Revolut 2026-09.pdf")] = {"id": "old", "data": b"x"}
    b = {"r1": msg("x@revolut.com", "Account statement", "s.pdf", b"%PDF-R3")}
    s = run({}, d, business_msgs=b)
    assert s["accounts"]["business"]["revolut_existing"] == 1
    assert d.files[(archive.accountant_folder_id(), "Revolut 2026-09.pdf")]["id"] == "old"


def test_helpers():
    assert archive.supplier_name("OpenAI <billing@mail.openai.com>") == "Openai"
    assert archive.supplier_name("x@shop.example.co.uk") == "Example"
    assert archive.safe_name('a/b:c.pdf') == "a_b_c.pdf"
    late = datetime(2026, 11, 3, tzinfo=timezone.utc)
    assert archive.detect_statement_period(b"not a pdf", late) == "2026-10"
