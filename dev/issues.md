# Issues

## 2026-7-12

Please reviewing the current markdown to PDF generation tool and have identified two issues:
1. Mermaid diagrams rendered in the PDF have extremely low resolution; text within complex diagrams is illegible.
2. Mathematical formulas wrapped in `$$` fail to render properly and remain as raw plain text.

## 2026-7-13

- When I launch Dogent in the samples directory and instruct it to convert the Markdown file containing Mermaid diagrams, "markdown_with_large_mermaid.md", into a PDF file, Dogent invokes the tool `dogent_export_document`. However, the Mermaid graphics fail to render in the exported PDF "markdown_with_large_mermaid.pdf", only a placeholder broken-image icon along with the text "Mermaid diagram 1" is displayed.
- Additionally, mathematical formulas wrapped with `$$` in the Markdown source remain as raw symbols in PDFs exported via `dogent_export_document`, without proper formula rendering.
- Inline athematical formulas wrapped with `$` in one line in the Markdown source remain as raw symbols in PDFs exported via `dogent_export_document`, without proper formula rendering.
 