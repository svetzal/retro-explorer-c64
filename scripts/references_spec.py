"""Executable behavior for resumable local references."""

import hashlib
import io
import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
import setup
from PIL import Image, ImageDraw, ImageFont
from references import (
    ConversionError,
    ConversionProfile,
    ConvertedPage,
    DoclingGateway,
    Resource,
    conversion_profile,
    convert,
    export_page,
)


@pytest.fixture
def document_gateway() -> Mock:
    gateway = Mock(spec=DoclingGateway)
    gateway.page_count.return_value = 2
    gateway.profile.return_value = conversion_profile()
    return gateway


class DescribeReferenceConversion:
    def should_reuse_the_original_checkpoint_wire_format(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        # Captured v1 format and canonical key from the pre-refactor converter.
        profile = {
            "format": 1,
            "docling": "2.150.0",
            "docling-core": "2.107.0",
            "rapidocr": "3.10.0",
            "ocr": "rapidocr-onnx-full-page",
            "language": "en",
            "tables": True,
        }
        key = "6f6cd40c208f838ed6a9d273359e52e1f031eef0087d1cec8890038abba9351f"
        directory = book / "docling-pages" / key
        directory.mkdir(parents=True)
        checkpoint = directory / "00001.json"
        original = json.dumps(
            {
                "identity": {"sha256": resource.sha256, "profile": profile},
                "page": 1,
                "markdown": "Previously converted page",
                "document": {},
            }
        )
        checkpoint.write_text(original)
        document_gateway.profile.return_value = ConversionProfile.model_validate(profile)
        document_gateway.convert_page.side_effect = ConversionError("model offline")

        convert(resource, book, (1, 1), documents=document_gateway)

        assert "Previously converted page" in (book / "text.md").read_text()
        assert checkpoint.read_text() == original
        assert (
            json.loads((book / "extraction.json").read_text())["checkpoints"]
            == f"docling-pages/{key}"
        )

    def should_resume_successful_pages_after_a_model_failure(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        first = ConvertedPage(markdown="# First page\n\nOriginal text.", document={})
        second = ConvertedPage(markdown="# Second page\n\nMore text.", document={})
        document_gateway.convert_page.side_effect = [first, ConversionError("model unavailable")]

        with pytest.raises(ConversionError, match="model unavailable"):
            convert(resource, book, documents=document_gateway)

        assert json.loads((book / "extraction.json").read_text())["completed_pages"] == [1]
        checkpoint = next((book / "docling-pages").rglob("00001.json"))
        saved = checkpoint.read_bytes()
        document_gateway.convert_page.side_effect = [second]

        convert(resource, book, documents=document_gateway)

        text = (book / "text.md").read_text()
        assert "First page" in text and "Second page" in text
        assert checkpoint.read_bytes() == saved
        assert json.loads((book / "extraction.json").read_text())["completed_pages"] == [1, 2]
        document_gateway.convert_page.side_effect = ConversionError("model offline")

        convert(resource, book, page_range=(1, 1), documents=document_gateway)

        assert (book / "text.md").read_text() == text

    def should_start_fresh_when_the_converter_profile_changes(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        document_gateway.convert_page.return_value = ConvertedPage(markdown="old", document={})
        convert(resource, book, (1, 1), documents=document_gateway)
        document_gateway.profile.return_value = conversion_profile().model_copy(
            update={"docling": "next"}
        )
        document_gateway.convert_page.return_value = ConvertedPage(markdown="new", document={})

        convert(resource, book, (1, 1), documents=document_gateway)

        assert "new" in (book / "text.md").read_text()
        assert len(list((book / "docling-pages").iterdir())) == 2

    def should_preserve_existing_output_when_the_first_page_fails(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        (book / "text.md").write_text("existing output")
        document_gateway.convert_page.side_effect = ConversionError("conversion failed")

        with pytest.raises(ConversionError):
            convert(resource, book, documents=document_gateway)

        assert (book / "text.md").read_text() == "existing output"

    @pytest.mark.parametrize("page_range", [(0, 1), (2, 1), (1, 99)])
    def should_reject_out_of_bounds_page_ranges(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
        page_range: tuple[int, int],
    ) -> None:
        with pytest.raises(ValueError, match="Page range"):
            convert(resource, book, page_range, documents=document_gateway)

        assert not (book / "text.md").exists()

    def should_reject_a_damaged_source(self, resource: Resource, book: Path) -> None:
        (book / "source.pdf").write_bytes(b"damaged")

        with pytest.raises(ValueError, match="checksum"):
            convert(resource, book)

        assert not (book / "text.md").exists()

    @pytest.mark.parametrize("damage", ["identity", "page", "filename"])
    def should_reject_invalid_checkpoints(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
        damage: str,
    ) -> None:
        document_gateway.convert_page.return_value = ConvertedPage(markdown="original", document={})
        convert(resource, book, (1, 1), documents=document_gateway)
        checkpoint = next((book / "docling-pages").rglob("00001.json"))
        record = json.loads(checkpoint.read_text())
        if damage == "identity":
            record["identity"]["sha256"] = "0" * 64
        elif damage == "page":
            record["page"] = 99
        else:
            checkpoint.rename(checkpoint.with_name("00002.json"))
            checkpoint = checkpoint.with_name("00002.json")
        checkpoint.write_text(json.dumps(record))
        saved = (book / "text.md").read_bytes()

        with pytest.raises(ValueError, match="Invalid checkpoint"):
            convert(resource, book, documents=document_gateway)

        assert (book / "text.md").read_bytes() == saved

    @pytest.mark.parametrize("damage", ["missing", "changed"])
    def should_repair_missing_or_changed_images_without_reconverting_other_pages(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
        damage: str,
    ) -> None:
        image = Image.new("RGB", (12, 12), "red")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        name = "page-00001-figure-001.png"
        page = ConvertedPage(
            markdown=f"![Figure](images/{name})",
            document={},
            images={name: buffer.getvalue()},
        )
        document_gateway.convert_page.side_effect = [
            page,
            ConvertedPage(markdown="Page two", document={}),
        ]
        convert(resource, book, documents=document_gateway)
        text = (book / "text.md").read_text()
        image_path = book / re.search(r"!\[Figure\]\(([^)]+)\)", text).group(1)
        assert image_path.read_bytes() == buffer.getvalue()
        with Image.open(image_path) as saved:
            assert saved.getpixel((0, 0)) == (255, 0, 0)
        if damage == "missing":
            image_path.unlink()
        else:
            image_path.write_bytes(b"damaged")
        document_gateway.convert_page.side_effect = [page]

        convert(resource, book, documents=document_gateway)

        assert image_path.read_bytes() == buffer.getvalue()
        assert "Page two" in (book / "text.md").read_text()
        document_gateway.convert_page.side_effect = ConversionError("offline")
        convert(resource, book, documents=document_gateway)
        assert (book / "text.md").read_text() == text

    def should_not_commit_a_checkpoint_when_image_storage_fails(
        self,
        resource: Resource,
        book: Path,
        document_gateway: Mock,
    ) -> None:
        from references import ConversionIdentity

        identity = ConversionIdentity(sha256=resource.sha256, profile=document_gateway.profile())
        directory = book / "docling-pages" / identity.checkpoint_key()
        directory.mkdir(parents=True)
        (directory / "images").write_text("a file blocks the image directory")
        (book / "text.md").write_text("previous output")
        document_gateway.convert_page.return_value = ConvertedPage(
            markdown="figure",
            document={},
            images={"page-00001-full.png": b"image"},
        )

        with pytest.raises(OSError):
            convert(resource, book, (1, 1), documents=document_gateway)

        assert not (directory / "00001.json").exists()
        assert (book / "text.md").read_text() == "previous output"

    @pytest.mark.integration
    def should_report_a_real_pdf_backend_failure(self, tmp_path: Path) -> None:
        source = tmp_path / "broken.pdf"
        source.write_bytes(b"%PDF-broken")

        with pytest.raises(ConversionError, match="PDF page 1"):
            DoclingGateway().convert_page(source, 1)

    @pytest.mark.integration
    @pytest.mark.parametrize("blank_primary_render", [False, True])
    def should_convert_a_scanned_pdf_through_setup_and_keep_original_page_numbers(
        self,
        tmp_path: Path,
        blank_primary_render: bool,
    ) -> None:
        image = Image.fromarray(np.full((1100, 850, 3), 255, dtype=np.uint8))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=28)
        draw.text((60, 80), "C64 REFERENCE TEST", font=font, fill="black")
        draw.text((60, 150), "A register holds a value.", font=font, fill="black")
        directory = tmp_path / "local/references/scan"
        directory.mkdir(parents=True)
        source = directory / "source.pdf"
        Image.new("RGB", image.size, "white").save(
            source,
            "PDF",
            resolution=100,
            save_all=True,
            append_images=[image],
        )
        resource = Resource(
            id="scan",
            title="Original scan",
            url="https://example.org/test-scan.pdf",
            sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            redistribution="Original test scan.",
        )
        (tmp_path / "resources.json").write_text(json.dumps([resource.model_dump()]))

        gateway = DoclingGateway()
        if blank_primary_render:
            gateway.converter = Mock()
            gateway.converter.convert.return_value = blank_conversion(2)
        result = setup.main(["--target", "c64-pal", "--pages", "2:2"], tmp_path, documents=gateway)

        assert result == 0
        assert "1/2 PDF pages converted with Docling" in (tmp_path / "local/INDEX.md").read_text()
        text = (directory / "text.md").read_text()
        assert "C64 REFERENCE TEST" in text
        assert "A register holds a value." in text
        assert "## PDF page 2" in text
        checkpoint = json.loads(next((directory / "docling-pages").rglob("00002.json")).read_text())
        assert checkpoint["document"]["texts"][0]["prov"][0]["page_no"] == 2
        full_page = re.search(r"\[View full PDF page 2\]\(([^)]+)\)", text)
        assert full_page is not None
        with Image.open(directory / full_page.group(1)) as rendered:
            assert rendered.width > 850
            assert rendered.height > 1100
            assert rendered.convert("L").getextrema()[0] < 100
        assert "data:image" not in json.dumps(checkpoint)
        assert checkpoint["image_hashes"]

    @pytest.mark.integration
    def should_preserve_a_genuinely_blank_page(self, book: Path) -> None:
        gateway = DoclingGateway()
        gateway.fallback_converter = Mock()
        gateway.fallback_converter.convert.side_effect = AssertionError(
            "Blank source needs no retry"
        )

        page = gateway.convert_page(book / "source.pdf", 2)

        assert "View full PDF page 2" in page.markdown
        with Image.open(io.BytesIO(page.images["page-00002-full.png"])) as image:
            assert image.convert("L").getextrema() == (255, 255)

    @pytest.mark.parametrize("failure", ["status", "blank", "missing-image"])
    def should_reject_an_unusable_fallback(self, book: Path, failure: str) -> None:
        from docling.datamodel.base_models import ConversionStatus

        gateway = DoclingGateway()
        gateway.converter = Mock()
        gateway.converter.convert.return_value = blank_conversion(1)
        gateway.fallback_converter = Mock()
        failed = blank_conversion(1)
        if failure == "status":
            failed.status = ConversionStatus.FAILURE
        elif failure == "missing-image":
            failed.document.pages[1].image = None
        gateway.fallback_converter.convert.return_value = failed

        with pytest.raises(ConversionError, match="PDFium fallback"):
            gateway.convert_page(book / "source.pdf", 1)

    def should_replace_cached_blank_output_from_the_previous_renderer(
        self, resource: Resource, book: Path, document_gateway: Mock
    ) -> None:
        from references import ConversionIdentity, PageCheckpoint, ReferenceStore

        old = conversion_profile().model_copy(update={"format": 2})
        checkpoint = PageCheckpoint(
            identity=ConversionIdentity(sha256=resource.sha256, profile=old),
            page=1,
            markdown="OLD BLANK OUTPUT",
            document={},
        )
        ReferenceStore(book).save_checkpoint(checkpoint, {})
        document_gateway.convert_page.return_value = ConvertedPage(
            markdown="Recovered original text", document={}
        )

        convert(resource, book, (1, 1), documents=document_gateway)

        assert "Recovered original text" in (book / "text.md").read_text()
        assert "OLD BLANK OUTPUT" not in (book / "text.md").read_text()
        assert len(list((book / "docling-pages").iterdir())) == 2


def blank_conversion(number: int) -> SimpleNamespace:
    from docling.datamodel.base_models import ConversionStatus
    from docling_core.types.doc import DoclingDocument, ImageRef, Size

    document = DoclingDocument(name="Solid-colour renderer failure")
    image = Image.new("RGB", (100, 100), "white")
    ImageDraw.Draw(image).rectangle((1, 1, 98, 98), fill=(255, 255, 153))
    document.add_page(
        page_no=number,
        size=Size(width=100, height=100),
        image=ImageRef.from_pil(image, dpi=144),
    )
    return SimpleNamespace(status=ConversionStatus.SUCCESS, document=document)


class DescribeDoclingImageExport:
    def should_export_figures_and_page_context_as_png_links(self) -> None:
        from docling_core.types.doc import DoclingDocument, ImageRef, Size

        document = DoclingDocument(name="Original diagram")
        document.add_page(
            page_no=7,
            size=Size(width=200, height=200),
            image=ImageRef.from_pil(Image.new("RGB", (400, 400), "white"), dpi=144),
        )
        document.add_picture(
            image=ImageRef.from_pil(Image.new("RGB", (100, 80), "red"), dpi=144),
        )

        converted = export_page(document, 7)

        assert "![" in converted.markdown
        assert "](images/page-00007-figure-001.png)" in converted.markdown
        assert "[View full PDF page 7](images/page-00007-full.png)" in converted.markdown
        with Image.open(io.BytesIO(converted.images["page-00007-figure-001.png"])) as image:
            assert image.size == (100, 80)
            assert image.getpixel((0, 0)) == (255, 0, 0)
        assert "data:image" not in json.dumps(converted.document)
        assert "images" not in converted.model_dump()

    def should_report_a_missing_rendered_page(self) -> None:
        from docling_core.types.doc import DoclingDocument, Size

        document = DoclingDocument(name="No page raster")
        document.add_page(page_no=1, size=Size(width=200, height=200))

        with pytest.raises(ConversionError, match="Missing rendered image"):
            export_page(document, 1)

    def should_report_a_missing_figure_crop(self) -> None:
        from docling_core.types.doc import DoclingDocument, ImageRef, Size

        document = DoclingDocument(name="No figure raster")
        document.add_page(
            page_no=1,
            size=Size(width=200, height=200),
            image=ImageRef.from_pil(Image.new("RGB", (400, 400), "white"), dpi=144),
        )
        document.add_picture()

        with pytest.raises(ConversionError, match="Missing figure"):
            export_page(document, 1)
