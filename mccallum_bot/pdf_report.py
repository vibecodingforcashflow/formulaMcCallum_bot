"""Отчёт: PDF через WeasyPrint, PNG — растр первой страницы (PyMuPDF)."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from mccallum_bot.formulas import LABEL_RU, ORDER, color_class, pct_of_ideal

_ROOT = Path(__file__).resolve().parent
_TEMPLATES = _ROOT / "templates"
_STATIC = _ROOT / "static"

TITLE_DEFAULT = "Пропорциональное телосложение по формуле МакКаллума"


def build_measurement_rows(
    ideal: dict[str, float], actual: dict[str, float]
) -> list[dict]:
    rows: list[dict] = []
    for key in ORDER:
        a = float(actual[key])
        i = float(ideal[key])
        rows.append(
            {
                "name": LABEL_RU[key],
                "ideal": i,
                "actual": a,
                "pct": pct_of_ideal(a, i),
                "cls": color_class(key, a, i),  # type: ignore[arg-type]
            }
        )
    return rows


def _jpeg_data_uri(static_dir: Path) -> str:
    path = static_dir / "mccallum_reference.jpg"
    if not path.is_file():
        raise FileNotFoundError(f"Нет файла иллюстрации: {path}")
    b64 = base64.standard_b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def render_mccallum_pdf(
    *,
    ideal: dict[str, float],
    actual: dict[str, float],
    title: str = TITLE_DEFAULT,
    templates_dir: Path | None = None,
    static_dir: Path | None = None,
) -> bytes:
    tdir = templates_dir or _TEMPLATES
    sdir = static_dir or _STATIC
    rows = build_measurement_rows(ideal, actual)
    ref_uri = _jpeg_data_uri(sdir)
    env = Environment(
        loader=FileSystemLoader(str(tdir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tpl = env.get_template("report_pdf.html")
    html_out = tpl.render(
        rows=rows,
        title=title,
        reference_image_data_uri=ref_uri,
    )
    doc = HTML(string=html_out, base_url=str(tdir))
    return doc.write_pdf(optimize_images=True, presentational_hints=True)


def pdf_first_page_png(pdf_bytes: bytes, *, zoom: float = 3.6) -> bytes:
    """Высокое разрешение: zoom × относительно точек PDF (≈72 dpi)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")
    finally:
        doc.close()


def _trim_png_bottom_uniform_footer(png_bytes: bytes) -> bytes:
    """Убрать однотонный низ (белый или фон страницы), чтобы блок отчёта занимал кадр."""
    img = Image.open(BytesIO(png_bytes)).convert("RGB")
    w, h = img.size
    px = img.load()
    ref = px[min(4, w - 1), h - 1]

    def near_ref(p: tuple[int, ...], tol: int = 30) -> bool:
        return sum(abs(p[i] - ref[i]) for i in range(3)) <= tol * 3

    y = h - 1
    min_y = max(1, h // 5)
    while y > min_y:
        step = max(1, w // 160)
        samples = [px[x, y] for x in range(0, w, step)]
        if sum(1 for p in samples if near_ref(p)) < len(samples) * 0.96:
            break
        y -= 1
    pad = max(6, h // 200)
    y2 = min(h - 1, y + pad)
    if y2 < h - 8:
        img = img.crop((0, 0, w, y2 + 1))
    out = BytesIO()
    img.save(out, format="PNG", compress_level=2, optimize=True)
    return out.getvalue()


def render_mccallum_report_png(
    *,
    ideal: dict[str, float],
    actual: dict[str, float],
    title: str = TITLE_DEFAULT,
    templates_dir: Path | None = None,
    static_dir: Path | None = None,
    raster_zoom: float = 3.6,
) -> bytes:
    pdf_bytes = render_mccallum_pdf(
        ideal=ideal,
        actual=actual,
        title=title,
        templates_dir=templates_dir,
        static_dir=static_dir,
    )
    raw = pdf_first_page_png(pdf_bytes, zoom=raster_zoom)
    return _trim_png_bottom_uniform_footer(raw)
