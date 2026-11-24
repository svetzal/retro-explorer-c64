"""Validate reference records and resume Docling conversion at page boundaries."""

import hashlib
import io
import json
import tempfile
from datetime import date
from functools import cached_property
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import pypdfium2 as pdfium
from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints

if TYPE_CHECKING:
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DoclingDocument
    from PIL.Image import Image

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
ReferenceURL = Annotated[str, StringConstraints(pattern=r"^https?://")]
ImageName = Annotated[
    str, StringConstraints(pattern=r"^page-[0-9]{5}-(?:full|figure-[0-9]{3})\.png$")
]


class Reference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=1)
    url: ReferenceURL


class Resource(Reference):
    """One source PDF that setup can download and convert."""

    url: str = Field(pattern=r"^https://")
    sha256: Sha256
    redistribution: str = Field(min_length=1)


class WebContent(BaseModel):
    """The exact URL and format of one file to cache."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    url: ReferenceURL
    format: Literal["html", "txt"]

    def cache_path(self) -> Path:
        key = hashlib.sha256(self.url.encode()).hexdigest()[:16]
        return Path(key) / f"source.{self.format}"


class WebReference(Reference):
    """A web citation with an optional file to cache."""

    kind: Literal["web"]
    citation: str = Field(min_length=1)
    accessed: date
    notes: str = Field(min_length=1)
    archive_url: ReferenceURL | None = None
    related_links: dict[str, ReferenceURL] = Field(default_factory=dict)
    content: WebContent | None = None


class ConversionProfile(BaseModel):
    """The converter settings that determine whether a checkpoint is reusable."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)
    format: int = 1
    docling: str
    docling_core: str = Field(alias="docling-core")
    rapidocr: str
    ocr: str = "rapidocr-onnx-full-page"
    language: str = "en"
    tables: bool = True


class ConversionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)
    sha256: Sha256
    profile: ConversionProfile

    def checkpoint_key(self) -> str:
        """Keep the original canonical JSON encoding for existing checkpoints."""
        serialized = json.dumps(self.model_dump(by_alias=True), sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()


class ConvertedPage(BaseModel):
    model_config = ConfigDict(frozen=True)
    markdown: str
    document: dict[str, JsonValue]
    images: dict[ImageName, bytes] = Field(default_factory=dict, exclude=True)


class PageCheckpoint(ConvertedPage):
    identity: ConversionIdentity
    page: int = Field(ge=1)
    image_hashes: dict[ImageName, Sha256] = Field(default_factory=dict)


class Extraction(BaseModel):
    model_config = ConfigDict(frozen=True)
    sha256: Sha256
    profile: ConversionProfile
    pages: int = Field(ge=1)
    completed_pages: list[int]
    sparse_pages: list[int]
    status: str
    checkpoints: str


class ConversionError(RuntimeError):
    """The document backend failed to produce a complete page."""


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_text(path: Path, text: str) -> None:
    """Replace text only after the complete new file has been written."""
    atomic_bytes(path, text.encode("utf-8"))


def atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def png_bytes(image: "Image") -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def export_page(document: "DoclingDocument", number: int) -> ConvertedPage:
    """Export figure links and page context without embedding image data in text."""
    from docling_core.types.doc import ImageRefMode

    images = {}
    page = document.pages[number]
    if page.image is None:
        raise ConversionError(f"Missing rendered image for PDF page {number}")
    full_name = f"page-{number:05}-full.png"
    images[full_name] = png_bytes(page.image.pil_image)
    # Extract all crops before replacing the page image's in-memory reference.
    for index, picture in enumerate(document.pictures, 1):
        image = picture.get_image(document)
        if image is None or picture.image is None:
            raise ConversionError(f"Missing figure {index} image on PDF page {number}")
        name = f"page-{number:05}-figure-{index:03}.png"
        images[name] = png_bytes(image)
        picture.image = picture.image.model_copy(update={"uri": Path("images") / name})
    page.image = page.image.model_copy(update={"uri": Path("images") / full_name})
    markdown = document.export_to_markdown(image_mode=ImageRefMode.REFERENCED)
    markdown += f"\n\n[View full PDF page {number}](images/{full_name})\n"
    return ConvertedPage(markdown=markdown, document=document.export_to_dict(), images=images)


def low_contrast_image(image: "Image") -> bool:
    """Flag near-flat rasters for comparison with an independent source render."""
    low, high = image.convert("L").getextrema()
    return high - low < 32


def conversion_profile() -> ConversionProfile:
    return ConversionProfile(
        format=3,
        docling=version("docling"),
        docling_core=version("docling-core"),
        rapidocr=version("rapidocr"),
    )


class DoclingGateway:
    """Isolate PDF parsing and model execution from checkpoint behavior."""

    def profile(self) -> ConversionProfile:
        return conversion_profile()

    def page_count(self, source: Path) -> int:
        with pdfium.PdfDocument(source) as document:
            return len(document)

    @cached_property
    def converter(self) -> "DocumentConverter":
        return self.make_converter()

    @cached_property
    def fallback_converter(self) -> "DocumentConverter":
        return self.make_converter(pdfium_backend=True)

    def make_converter(self, *, pdfium_backend: bool = False) -> "DocumentConverter":
        # Cached and guidance-only runs do not initialize the model pipeline.
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import OcrMode, PdfPipelineOptions, RapidOcrOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        options = PdfPipelineOptions()
        options.do_ocr = True
        options.ocr_options = RapidOcrOptions(
            backend="onnxruntime",
            mode=OcrMode.FULL_PAGE,
            lang=["en"],
        )
        options.do_table_structure = True
        options.generate_picture_images = True
        options.generate_page_images = True
        options.images_scale = 2.0
        options.enable_remote_services = False
        pdf_options = PdfFormatOption(pipeline_options=options)
        if pdfium_backend:
            from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

            pdf_options.backend = PyPdfiumDocumentBackend
        return DocumentConverter(format_options={InputFormat.PDF: pdf_options})

    def convert_page(self, source: Path, number: int) -> ConvertedPage:
        """Normalize model/backend failures into a conversion error for the CLI."""
        from docling.datamodel.base_models import ConversionStatus

        try:
            result = self.converter.convert(source, page_range=(number, number))
            if result.status != ConversionStatus.SUCCESS:
                raise ConversionError(f"Docling did not finish PDF page {number}: {result.status}")
            page = result.document.pages[number]
            if page.image is not None and low_contrast_image(page.image.pil_image):
                with pdfium.PdfDocument(source) as original:
                    rendered = original[number - 1].render(scale=2).to_pil()
                if not low_contrast_image(rendered):
                    result = self.fallback_converter.convert(source, page_range=(number, number))
                    if result.status != ConversionStatus.SUCCESS:
                        raise ConversionError(f"PDFium fallback did not finish PDF page {number}")
                    fallback_page = result.document.pages[number]
                    if fallback_page.image is None or low_contrast_image(
                        fallback_page.image.pil_image
                    ):
                        raise ConversionError(f"PDFium fallback returned a blank PDF page {number}")
            return export_page(result.document, number)
        except Exception as error:
            raise ConversionError(f"PDF page {number}: {error}") from error


class ReferenceStore:
    """Read and publish a book's local files without exposing partial checkpoints."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.source = directory / "source.pdf"

    def validate_source(self, resource: Resource) -> None:
        if digest(self.source) != resource.sha256:
            raise ValueError("Source PDF checksum differs from the manifest")

    def checkpoint_directory(self, identity: ConversionIdentity) -> Path:
        return self.directory / "docling-pages" / identity.checkpoint_key()

    def read_checkpoints(
        self,
        identity: ConversionIdentity,
        total: int,
    ) -> dict[int, PageCheckpoint]:
        completed = {}
        for path in self.checkpoint_directory(identity).glob("*.json"):
            record = PageCheckpoint.model_validate_json(path.read_text())
            if (
                record.identity != identity
                or record.page > total
                or path.stem != f"{record.page:05}"
            ):
                raise ValueError(f"Invalid checkpoint: {path}")
            if self.images_available(record):
                completed[record.page] = record
        return completed

    def images_available(self, checkpoint: PageCheckpoint) -> bool:
        directory = self.checkpoint_directory(checkpoint.identity) / "images"
        return all(
            (directory / name).is_file() and digest(directory / name) == checksum
            for name, checksum in checkpoint.image_hashes.items()
        )

    def save_checkpoint(self, checkpoint: PageCheckpoint, images: dict[str, bytes]) -> None:
        directory = self.checkpoint_directory(checkpoint.identity)
        for name, content in images.items():
            atomic_bytes(directory / "images" / name, content)
        # The checkpoint commits the page only after every image has been saved.
        path = directory / f"{checkpoint.page:05}.json"
        atomic_text(path, checkpoint.model_dump_json(by_alias=True) + "\n")

    def publish(
        self, resource: Resource, extraction: Extraction, pages: list[PageCheckpoint]
    ) -> None:
        atomic_text(self.directory / "text.md", reference_markdown(resource, extraction, pages))
        atomic_text(
            self.directory / "extraction.json",
            extraction.model_dump_json(indent=2, by_alias=True) + "\n",
        )


def summarize(
    identity: ConversionIdentity,
    total: int,
    completed: dict[int, PageCheckpoint],
) -> Extraction:
    sparse = [
        number for number, page in sorted(completed.items()) if len(page.markdown.strip()) < 80
    ]
    return Extraction(
        sha256=identity.sha256,
        profile=identity.profile,
        pages=total,
        completed_pages=sorted(completed),
        sparse_pages=sparse,
        status=(
            f"{len(completed)}/{total} PDF pages converted with Docling; {len(sparse)} sparse pages; "
            f"{sum(len(page.image_hashes) for page in completed.values())} linked images"
        ),
        checkpoints=f"docling-pages/{identity.checkpoint_key()}",
    )


def reference_markdown(
    resource: Resource, extraction: Extraction, pages: list[PageCheckpoint]
) -> str:
    header = (
        f"# {resource.title}\n\nSource: {resource.url}\n\n"
        f"SHA-256: {resource.sha256}\n\n{extraction.status}.\n\n"
        "PDF page numbers include covers. OCR is unverified. "
        "Open linked figures or full-page images for diagrams and ambiguous code.\n\n"
    )
    body = "\n".join(
        f"## PDF page {page.page}\n\n{linked_page_markdown(page, extraction.checkpoints)}\n"
        for page in pages
    )
    return header + body


def linked_page_markdown(page: PageCheckpoint, checkpoints: str) -> str:
    markdown = page.markdown
    for name in page.image_hashes:
        markdown = markdown.replace(f"](images/{name})", f"]({checkpoints}/images/{name})")
    return markdown


def convert(
    resource: Resource,
    directory: Path,
    page_range: tuple[int, int] | None = None,
    *,
    documents: DoclingGateway | None = None,
) -> str:
    """Convert missing pages, retaining complete checkpoints even after failure."""
    documents = documents or DoclingGateway()
    store = ReferenceStore(directory)
    store.validate_source(resource)
    total = documents.page_count(store.source)
    first, last = page_range or (1, total)
    if not 1 <= first <= last <= total:
        raise ValueError(f"Page range must be within 1..{total}")
    identity = ConversionIdentity(sha256=resource.sha256, profile=documents.profile())
    completed = store.read_checkpoints(identity, total)
    try:
        for number in range(first, last + 1):
            if number in completed:
                print(f"  Reusing PDF page {number}/{total}", flush=True)
                continue
            print(f"  Docling PDF page {number}/{total}", flush=True)
            page = documents.convert_page(store.source, number)
            checkpoint = PageCheckpoint(
                identity=identity,
                page=number,
                **page.model_dump(),
                image_hashes={
                    name: hashlib.sha256(data).hexdigest() for name, data in page.images.items()
                },
            )
            store.save_checkpoint(checkpoint, page.images)
            completed[number] = checkpoint
    finally:
        if completed:
            extraction = summarize(identity, total, completed)
            store.publish(resource, extraction, [completed[n] for n in sorted(completed)])
    return extraction.status
