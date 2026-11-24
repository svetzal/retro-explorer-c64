"""Original reference fixtures shared by the co-located specifications."""

import hashlib
import http.server
import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from references import Resource


@pytest.fixture
def pdf_bytes() -> bytes:
    """An original two-page PDF: text followed by a blank page."""
    text = b"BT /F1 12 Tf 40 700 Td (Original starter kit test reference.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n" + text + b"\nendstream",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>",
    ]
    output = b"%PDF-1.4\n"
    offsets = []
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    output += b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets)
    output += f"trailer\n<< /Size 7 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return output


@pytest.fixture
def resource(pdf_bytes: bytes) -> Resource:
    return Resource(
        id="test-book",
        title="Original reference",
        url="https://example.org/test.pdf",
        sha256=hashlib.sha256(pdf_bytes).hexdigest(),
        redistribution="Original test file.",
    )


@pytest.fixture
def project(tmp_path: Path, resource: Resource) -> Path:
    (tmp_path / "resources.json").write_text(json.dumps([resource.model_dump()]))
    return tmp_path


@pytest.fixture
def book(tmp_path: Path, pdf_bytes: bytes) -> Path:
    (tmp_path / "source.pdf").write_bytes(pdf_bytes)
    return tmp_path


@pytest.fixture
def pdf_server(pdf_bytes: bytes) -> Iterator[str]:
    web = {
        "/guide": ("text/html", b"<article><h1>Copper guide</h1></article>\n"),
        "/wall.s": ("text/plain", b"draw_wall:\n\trts\n"),
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in web:
                media_type, body = web.pop(self.path)
                self.send_response(200)
                self.send_header("Content-Type", media_type)
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path in {"/guide", "/wall.s"}:
                self.send_error(410)
                return
            if self.path == "/missing":
                self.send_error(404)
                return
            body = b"not a PDF" if self.path == "/invalid" else pdf_bytes
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            if self.path == "/mislabelled.pdf":
                self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        worker.join()
        server.server_close()
