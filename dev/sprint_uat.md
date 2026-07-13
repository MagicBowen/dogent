# User Acceptance Testing (UAT)

Example：

```
### Story 1 – Package & Entrypoint
1) Install editable: `pip install -e .`
2) Run `dogent -h` for help and `dogent -v` for version.
3) Run `dogent` (any directory). Expect the Dogent prompt and help message.

User Test Results: Accepted (2026-02-03)
```

---

## 2026-7-13 PDF Export Rendering Fixes

### Story 1 – Render Mermaid SVGs in Exported PDFs

1. Install the working tree with `pip install -e .`.
2. Change to the `samples` directory and run `dogent`.
3. Ask Dogent to export `markdown_with_large_mermaid.md` to
   `markdown_with_large_mermaid-fixed.pdf` using `dogent_export_document`.
4. Open the PDF. Expect the complete CI pipeline diagram to be visible, with no
   broken-image icon or `Mermaid diagram 1` placeholder text.
5. Zoom in on diagram labels. Expect the text and lines to remain sharp.

User Test Results: Accepted (2026-07-13)

### Story 2 – Render Inline and Display Math in Exported PDFs

1. From the `samples` directory, run `dogent`.
2. Create `markdown_with_math.md` in the `samples` directory with this content:

   ````markdown
   # Math Rendering Sample

   Einstein wrote $E = mc^2$ in one line.

   Currency remains literal: $5.00.

   Inline code remains literal: `$x + y$`.

   $$
   \frac{a}{b} = c^2
   $$

   $$ \sum_{i=1}^{n} i
   = \frac{n(n+1)}{2} $$

   ```text
   $$ not rendered as math $$
   ```
   ````

3. Ask Dogent to export `markdown_with_math.md` to `markdown_with_math.pdf` using
   `dogent_export_document`.
4. Open the PDF. Expect the inline energy formula, fraction equation, and summation
   equation to be typeset; no `$` or `$$` delimiters should surround rendered math.
5. Expect `$5.00` to remain currency and `$x + y$` to remain literal inside inline
   code.
6. Inspect the fenced text example. Expect `$$ not rendered as math $$` to remain
   literal inside the code block.

UAT Feedback (2026-07-13): Inline formulas wrapped in `$` remained raw in PDF output.

Fix Status: Inline math rendering added and verified in a real PDF.

User Test Results: Accepted (2026-07-13)
