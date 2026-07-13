# Design

## 2026-7-13 PDF Export Rendering Fixes

### Problem Analysis

- Mermaid rendering returned `svg.outerHTML` after inserting Mermaid output into an
  HTML document. HTML serialization changed XHTML line breaks inside SVG
  `foreignObject` nodes from `<br/>` to `<br>`. The resulting file was not valid
  standalone XML, so Chromium could not decode the inlined SVG image while printing
  the PDF and displayed the image alt text instead.
- Display-math detection handled only `$$` blocks whose delimiters were either both
  on one line or each alone on separate lines. A formula spanning lines when content
  shared a delimiter line was left unchanged and subsequently rendered as literal
  Markdown text.
- Inline `$...$` formulas had no Markdown parsing rule, so they always remained raw
  text in the generated HTML and PDF.

### Design

- Serialize the rendered Mermaid SVG with the browser's `XMLSerializer` so embedded
  XHTML remains valid XML while retaining intrinsic SVG dimensions and vector output.
- Recognize paired display-math delimiters across one or more lines, allowing formula
  content next to either delimiter. Continue excluding fenced code blocks from math
  conversion.
- Parse paired `$...$` formulas as inline MathML during Markdown inline tokenization.
  Require same-line, non-whitespace delimiters and preserve escaped dollars, currency
  without a closing delimiter, inline code spans, and fenced code as literal text.
- Cover both regressions with focused unit tests and verify the real Playwright PDF
  output using the reported large Mermaid sample plus a math-rendering sample.
