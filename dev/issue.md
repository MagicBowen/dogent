In the latest modification, the images still cannot be displayed properly. However, in one of your previous modifications, they could be displayed. But I accidentally rolled back that code change. The specific modifications at that time are as follows:

```sh
• Edited dogent/document_io.py (+21 -2)
      3  import asyncio
      4 +import base64
      5 +import mimetypes
      6 +import re
      7  import shutil
        ⋮
     15  from typing import Any, Iterable
     16 +from urllib.parse import unquote, urlparse
     17
        ⋮
    549
    546 -def _markdown_to_html(md_text: str, *, title: str, css_text: str | None = None) -> str:
    550 +def _markdown_to_html(
    551 +    md_text: str,
    552 +    *,
    553 +    title: str,
    554 +    css_text: str | None = None,
    555 +    base_dir: Path | None = None,
    556 +    workspace_root: Path | None = None,
    557 +) -> str:
    558      from markdown_it import MarkdownIt
        ⋮
    585      body = mdi.render(md_text)
    586 +    if base_dir:
    587 +        body = _inline_local_images(body, base_dir, workspace_root)
    588      css = css_text if css_text is not None else _default_pdf_css()
        ⋮
    609      header_template, footer_template = _build_pdf_header_footer(css_text)
    597 -    html = _markdown_to_html(md_text, title=title or "Document", css_text=css_text)
    610 +    html = _markdown_to_html(
    611 +        md_text,
    612 +        title=title or "Document",
    613 +        css_text=css_text,
    614 +        base_dir=md_path.parent,
    615 +        workspace_root=workspace_root,
    616 +    )
    617      await _html_to_pdf(

• Edited dogent/document_io.py (+47 -0)
    599
    600 +def _inline_local_images(
    601 +    html: str,
    602 +    base_dir: Path,
    603 +    workspace_root: Path | None,
    604 +) -> str:
    605 +    img_pattern = re.compile(
    606 +        r'(<img\\b[^>]*\\bsrc=)(["\\\']?)([^"\\\'>\\s]+)\\2',
    607 +        re.IGNORECASE,
    608 +    )
    609 +
    610 +    def replace(match: re.Match[str]) -> str:
    611 +        prefix, quote, src = match.groups()
    612 +        new_src = _to_data_uri(src, base_dir, workspace_root)
    613 +        if not new_src:
    614 +            return match.group(0)
    615 +        q = quote or '"'
    616 +        return f"{prefix}{q}{new_src}{q}"
    617 +
    618 +    return img_pattern.sub(replace, html)
    619 +
    620 +
    621 +def _to_data_uri(
    622 +    src: str,
    623 +    base_dir: Path,
    624 +    workspace_root: Path | None,
    625 +) -> str | None:
    626 +    parsed = urlparse(src)
    627 +    if parsed.scheme in {"http", "https", "data", "file"}:
    628 +        return None
    629 +    raw_path = unquote(parsed.path)
    630 +    path = Path(raw_path)
    631 +    if not path.is_absolute():
    632 +        path = (base_dir / path).resolve()
    633 +    else:
    634 +        path = path.resolve()
    635 +    if workspace_root:
    636 +        try:
    637 +            path.relative_to(workspace_root.resolve())
    638 +        except Exception:
    639 +            return None
    640 +    if not path.exists() or not path.is_file():
    641 +        return None
    642 +    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    643 +    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    644 +    return f"data:{mime};base64,{encoded}"
    645 +
    646 +
    647  async def _markdown_to_pdf(

• Edited tests/test_document_io.py (+20 -0)
    173
    174 +    def test_markdown_to_html_inlines_local_images(self) -> None:
    175 +        png_bytes = (
    176 +            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    177 +            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    178 +            b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x01"
    179 +            b"\x01\x01\x00\x18\xdd\x8d\xdb\x00\x00\x00\x00IEND\xaeB`\x82"
    180 +        )
    181 +        with tempfile.TemporaryDirectory() as tmp:
    182 +            base_dir = Path(tmp)
    183 +            img_path = base_dir / "img.png"
    184 +            img_path.write_bytes(png_bytes)
    185 +            md = "![alt](img.png)"
    186 +            html = document_io._markdown_to_html(
    187 +                md,
    188 +                title="Images",
    189 +                base_dir=base_dir,
    190 +                workspace_root=base_dir,
    191 +            )
    192 +            self.assertIn("data:image/png;base64", html)
    193 +
    194

• Ran python -m unittest discover -s tests -v
  └ /usr/local/Homebrew/Library/Homebrew/cmd/shellenv.sh: line 21: /bin/ps: Operation not permitted
    test_finalize_aborted_records_status (test_agent_display.AgentDisplayTests) ... ok
    … +312 lines
    FAILED (failures=1)
    sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute

• Edited dogent/document_io.py (+1 -1)
    605      img_pattern = re.compile(
    606 -        r'(<img\\b[^>]*\\bsrc=)(["\\\']?)([^"\\\'>\\s]+)\\2',
    606 +        r'(<img\b[^>]*\bsrc=)(["\']?)([^"\'>\s]+)\2',
    607          re.IGNORECASE,

• Ran python -m unittest tests.test_document_io.DocumentIOTests.test_markdown_to_html_inlines_local_images -v
  └ /usr/local/Homebrew/Library/Homebrew/cmd/shellenv.sh: line 21: /bin/ps: Operation not permitted
    test_document_io (unittest.loader._FailedTest) ... ERROR
    … +13 lines

    FAILED (errors=1)

• Ran python -m unittest discover -s tests -p "test_document_io.py" -v
  └ /usr/local/Homebrew/Library/Homebrew/cmd/shellenv.sh: line 21: /bin/ps: Operation not permitted
    test_convert_docx_to_markdown_with_extract_media (test_document_io.DocumentConversionTests) ... Executing <Task
    … +25 lines
    OK
    sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute

• Ran python -m unittest discover -s tests -v
  └ /usr/local/Homebrew/Library/Homebrew/cmd/shellenv.sh: line 21: /bin/ps: Operation not permitted
    test_finalize_aborted_records_status (test_agent_display.AgentDisplayTests) ... ok
    … +304 lines
    OK
    sys:1: DeprecationWarning: builtin type swigvarlink has no __module__ attribute

─ Worked for 2m 32s ────────────────────────────────────────────────────────────────────────────────────────────────────

• Fixed Markdown image embedding for PDF export by inlining local images as data URIs, so ![]() now renders in PDFs.
  Updated tests to cover image inlining.

  Changes:

  - Image inlining + HTML rendering: dogent/document_io.py
  - Tests: tests/test_document_io.py

  Tests run:

  - python -m unittest discover -s tests -v
```