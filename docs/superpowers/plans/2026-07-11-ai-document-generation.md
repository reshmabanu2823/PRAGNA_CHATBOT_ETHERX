# AI Document Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user ask Pragna in plain chat language to generate a Word doc, Excel spreadsheet, PDF, or PowerPoint deck, and get a real downloadable file back as a chat attachment — the same way AI image generation already works.

**Architecture:** One backend module (`services/document_generator.py`) asks the LLM for a markdown outline, parses it into a shared `{title, sections}` structure, and hands that structure to one of four format-specific builder functions. Two new Flask routes generate and serve the file. The frontend detects a document-generation phrase the same way it already detects an image-generation phrase (duplicated regex + helper per call site), calls the new endpoint, and renders a real downloadable `type: "document"` attachment.

**Tech Stack:** Flask (`backend/app.py`), `python-docx`, `openpyxl`, `python-pptx` (new), `reportlab` (new), `services/llm.py`'s `generate_completion`, React/Vite frontend (`api.js`, `ChatWindow.jsx`, `InputBar.jsx`, `pragna/App.jsx`, `MessageBubble.jsx`).

## Global Constraints

- `backend/requirements.txt` already has `python-docx>=1.1.2` and `openpyxl>=3.1.5`; this plan adds `python-pptx` and `reportlab`.
- All content generation reuses `services/llm.py`'s `generate_completion(messages, model_override=None, fallback_models=None, language="en", chat_mode="general") -> str` — the same function `/api/summarize_chat` uses (`backend/app.py:2042-2054`).
- The shared structure every format builder consumes is exactly: `{"title": str, "sections": [{"heading": str, "bullets": [str, ...], "table": [[str, ...], ...] | None}, ...]}`. A section has either `bullets` (non-empty list, `table: None`) or `table` (non-empty list of rows, `bullets: []`) — never both populated.
- `POST /api/documents/generate` returns `{"download_url": "/api/documents/download/<filename>", "filename": "<display name>"}`. `GET /api/documents/download/<filename>` must reject path traversal and 404 on a missing file.
- Frontend detection mirrors the existing `IMAGE_REQUEST_RE` / `extractImagePrompt` pattern (`ChatWindow.jsx:7-15`, `InputBar.jsx:14-22`, `App.jsx:17-25`) — duplicated per call site, not shared/imported, matching this codebase's established convention for that pattern. The new document check runs *before* the image-request check in all three files.
- Out of scope (do not implement): editing a previously generated document, native PowerPoint tables (render as plain text lines instead), any file-browsing UI, automatic cleanup/expiry of `backend/generated_docs/`.
- This repo has no pytest suite — write new backend tests as standalone `test_*.py` scripts using plain `assert` statements and printed progress, run individually with `python test_x.py` (see `CLAUDE.md`).

---

### Task 1: Markdown outline parser + LLM content generation

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/services/document_generator.py`
- Test: `backend/test_document_generator.py`

**Interfaces:**
- Produces: `_parse_markdown_outline(text: str) -> dict` — pure parser, no I/O. Returns `{"title": str, "sections": [{"heading": str, "bullets": [str], "table": [[str]] | None}]}`.
- Produces: `generate_document_structure(prompt: str, language: str = "en") -> dict` — calls `generate_completion` then `_parse_markdown_outline`. Used by Task 3's route.

- [ ] **Step 1: Add new dependencies**

Edit `backend/requirements.txt`, in the "Upload/document analysis" section (currently):
```
# Upload/document analysis
pypdf>=4.3.1
python-docx>=1.1.2
openpyxl>=3.1.5
```
Change to:
```
# Upload/document analysis
pypdf>=4.3.1
python-docx>=1.1.2
openpyxl>=3.1.5
python-pptx>=1.0.2
reportlab>=4.2.0
```

- [ ] **Step 2: Install the new dependencies**

Run: `cd backend && pip install python-pptx>=1.0.2 reportlab>=4.2.0`
Expected: both packages install with no errors.

- [ ] **Step 3: Write the failing test for the parser**

Create `backend/test_document_generator.py`:
```python
"""Test _parse_markdown_outline parsing logic (no LLM calls required)."""
from services.document_generator import _parse_markdown_outline

SAMPLE = """# Quarterly Report
## Overview
- Revenue grew 12%
- Costs remained flat
## Financial Summary
| Quarter | Revenue |
| Q1 | 100 |
| Q2 | 112 |
"""


def test_title_and_sections():
    result = _parse_markdown_outline(SAMPLE)
    assert result["title"] == "Quarterly Report", result
    assert len(result["sections"]) == 2, result
    print("PASS: title and section count")


def test_bullets_section():
    result = _parse_markdown_outline(SAMPLE)
    overview = result["sections"][0]
    assert overview["heading"] == "Overview", overview
    assert overview["bullets"] == ["Revenue grew 12%", "Costs remained flat"], overview
    assert overview["table"] is None, overview
    print("PASS: bullets section parsed correctly")


def test_table_section():
    result = _parse_markdown_outline(SAMPLE)
    financials = result["sections"][1]
    assert financials["heading"] == "Financial Summary", financials
    assert financials["bullets"] == [], financials
    assert financials["table"] == [["Quarter", "Revenue"], ["Q1", "100"], ["Q2", "112"]], financials
    print("PASS: table section parsed correctly")


def test_untitled_fallback():
    result = _parse_markdown_outline("## Just a section\n- one bullet\n")
    assert result["title"] == "Untitled Document", result
    print("PASS: missing title falls back to 'Untitled Document'")


if __name__ == "__main__":
    test_title_and_sections()
    test_bullets_section()
    test_table_section()
    test_untitled_fallback()
    print("All document_generator parser tests passed.")
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && python test_document_generator.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.document_generator'`

- [ ] **Step 5: Implement the parser and content generation function**

Create `backend/services/document_generator.py`:
```python
"""Markdown-outline based content generation shared by all document formats
(Word, Excel, PDF, PowerPoint). See docs/superpowers/specs/2026-07-11-ai-document-generation-design.md.
"""
import re

from services.llm import generate_completion

_TABLE_SEPARATOR_RE = re.compile(r'^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$')


def _parse_markdown_outline(text):
    """Parse a markdown outline into {"title": str, "sections": [{"heading", "bullets", "table"}]}.

    A section ends up with either a populated `bullets` list (`table: None`) or a
    populated `table` (`bullets: []`) — never both, even if the source text mixed them.
    """
    title = ""
    sections = []
    current = None

    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith('# '):
            title = line[2:].strip()
            continue

        if line.startswith('## '):
            current = {"heading": line[3:].strip(), "bullets": [], "table": []}
            sections.append(current)
            continue

        if current is None:
            continue

        if line.startswith('|'):
            if _TABLE_SEPARATOR_RE.match(line):
                continue
            cells = [c.strip() for c in line.strip('|').split('|')]
            current["table"].append(cells)
            continue

        if line.startswith('- ') or line.startswith('* '):
            current["bullets"].append(line[2:].strip())
            continue

    for section in sections:
        if section["table"]:
            section["bullets"] = []
        else:
            section["table"] = None

    return {"title": title or "Untitled Document", "sections": sections}


def generate_document_structure(prompt, language="en"):
    """Ask the LLM for a markdown outline about `prompt` and parse it into a document structure."""
    system_prompt = (
        "You write structured outlines for documents. Given a subject, respond ONLY with "
        "a markdown outline in this exact shape:\n"
        "# <Title>\n"
        "## <Section heading>\n"
        "- <bullet point>\n"
        "- <bullet point>\n"
        "## <Another section heading>\n"
        "| <column> | <column> |\n"
        "| <value> | <value> |\n\n"
        "Use bullet points for narrative sections and a markdown table only for sections "
        "that are genuinely tabular data. Include 3-6 sections. Do not include any text "
        "outside the outline."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    outline_text = generate_completion(messages, language=language)
    return _parse_markdown_outline(outline_text)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python test_document_generator.py`
Expected: all 4 `PASS:` lines print, then `All document_generator parser tests passed.`

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/services/document_generator.py backend/test_document_generator.py
git commit -m "feat: add markdown outline parser for document generation"
```

---

### Task 2: Format builders (docx, pdf, pptx, xlsx)

**Files:**
- Modify: `backend/services/document_generator.py`
- Test: `backend/test_document_builders.py`

**Interfaces:**
- Consumes: the `{"title", "sections"}` structure shape defined in Task 1.
- Produces: `_build_docx(structure: dict, filepath: str) -> None`, `_build_pdf(structure: dict, filepath: str) -> None`, `_build_pptx(structure: dict, filepath: str) -> None`, `_build_xlsx(structure: dict, filepath: str) -> None` — each writes the file to `filepath` and returns nothing. Used by Task 3's route.

- [ ] **Step 1: Write the failing tests**

Create `backend/test_document_builders.py`:
```python
"""Test format builder functions produce valid, readable files."""
import os
import tempfile

from docx import Document as DocxReader
from openpyxl import load_workbook
from pptx import Presentation as PptxReader
from pypdf import PdfReader

from services.document_generator import _build_docx, _build_pdf, _build_pptx, _build_xlsx

STRUCTURE = {
    "title": "Test Document",
    "sections": [
        {"heading": "Overview", "bullets": ["Point one", "Point two"], "table": None},
        {"heading": "Numbers", "bullets": [], "table": [["Quarter", "Revenue"], ["Q1", "100"]]},
    ],
}

NO_TABLE_STRUCTURE = {
    "title": "Prose Only",
    "sections": [
        {"heading": "Intro", "bullets": ["First", "Second"], "table": None},
    ],
}


def test_docx():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.docx")
        _build_docx(STRUCTURE, path)
        assert os.path.getsize(path) > 0
        doc = DocxReader(path)
        text = "\n".join(p.text for p in doc.paragraphs)
        assert "Test Document" in text
        assert "Point one" in text
        assert len(doc.tables) == 1
        print("PASS: docx builder")


def test_pdf():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.pdf")
        _build_pdf(STRUCTURE, path)
        assert os.path.getsize(path) > 0
        reader = PdfReader(path)
        text = "".join(page.extract_text() or "" for page in reader.pages)
        assert "Test Document" in text
        print("PASS: pdf builder")


def test_pptx():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.pptx")
        _build_pptx(STRUCTURE, path)
        assert os.path.getsize(path) > 0
        prs = PptxReader(path)
        assert len(prs.slides) == 3  # title slide + 2 section slides
        assert prs.slides[0].shapes.title.text == "Test Document"
        print("PASS: pptx builder")


def test_xlsx_with_table():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.xlsx")
        _build_xlsx(STRUCTURE, path)
        wb = load_workbook(path)
        assert "Numbers" in wb.sheetnames
        ws = wb["Numbers"]
        assert ws["A1"].value == "Quarter"
        print("PASS: xlsx builder with table")


def test_xlsx_fallback_no_table():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "out.xlsx")
        _build_xlsx(NO_TABLE_STRUCTURE, path)
        wb = load_workbook(path)
        assert "Summary" in wb.sheetnames
        ws = wb["Summary"]
        assert ws["A1"].value == "Section"
        assert ws["A2"].value == "Intro"
        print("PASS: xlsx builder fallback sheet")


if __name__ == "__main__":
    test_docx()
    test_pdf()
    test_pptx()
    test_xlsx_with_table()
    test_xlsx_fallback_no_table()
    print("All document builder tests passed.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python test_document_builders.py`
Expected: FAIL with `ImportError: cannot import name '_build_docx' from 'services.document_generator'`

- [ ] **Step 3: Implement the four builders**

Append to `backend/services/document_generator.py` (add these imports at the top of the file, alongside the existing `import re` and `from services.llm import generate_completion`):
```python
from docx import Document
from openpyxl import Workbook
from pptx import Presentation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table as PdfTable, TableStyle
```

Then append these functions at the end of the file:
```python
def _build_docx(structure, filepath):
    doc = Document()
    doc.add_heading(structure["title"], level=0)
    for section in structure["sections"]:
        doc.add_heading(section["heading"], level=1)
        if section["table"]:
            rows = section["table"]
            table = doc.add_table(rows=len(rows), cols=len(rows[0]))
            table.style = "Table Grid"
            for r, row in enumerate(rows):
                for c, cell in enumerate(row):
                    table.cell(r, c).text = cell
        else:
            for bullet in section["bullets"]:
                doc.add_paragraph(bullet, style="List Bullet")
    doc.save(filepath)


def _build_pdf(structure, filepath):
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(structure["title"], styles["Title"]), Spacer(1, 12)]
    for section in structure["sections"]:
        story.append(Paragraph(section["heading"], styles["Heading2"]))
        story.append(Spacer(1, 6))
        if section["table"]:
            pdf_table = PdfTable(section["table"])
            pdf_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ]))
            story.append(pdf_table)
        else:
            for bullet in section["bullets"]:
                story.append(Paragraph(f"&bull; {bullet}", styles["Normal"]))
        story.append(Spacer(1, 12))
    doc.build(story)


def _build_pptx(structure, filepath):
    prs = Presentation()
    title_slide = prs.slides.add_slide(prs.slide_layouts[0])
    title_slide.shapes.title.text = structure["title"]

    for section in structure["sections"]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = section["heading"]
        body = slide.placeholders[1].text_frame
        body.clear()
        lines = section["bullets"] if section["bullets"] else [
            " | ".join(row) for row in (section["table"] or [])
        ]
        for i, line in enumerate(lines):
            if i == 0:
                body.text = line
            else:
                body.add_paragraph().text = line
    prs.save(filepath)


def _sanitize_sheet_name(name):
    cleaned = re.sub(r'[\[\]:*?/\\]', '', name or '').strip()
    return cleaned[:31] or "Sheet1"


def _build_xlsx(structure, filepath):
    wb = Workbook()
    wb.remove(wb.active)

    table_section = next((s for s in structure["sections"] if s["table"]), None)
    if table_section:
        ws = wb.create_sheet(_sanitize_sheet_name(table_section["heading"]))
        for row in table_section["table"]:
            ws.append(row)
    else:
        ws = wb.create_sheet("Summary")
        ws.append(["Section", "Content"])
        for section in structure["sections"]:
            ws.append([section["heading"], "; ".join(section["bullets"])])

    wb.save(filepath)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python test_document_builders.py`
Expected: all 5 `PASS:` lines print, then `All document builder tests passed.`

- [ ] **Step 5: Commit**

```bash
git add backend/services/document_generator.py backend/test_document_builders.py
git commit -m "feat: add docx/pdf/pptx/xlsx format builders for document generation"
```

---

### Task 3: Backend routes

**Files:**
- Modify: `backend/app.py` (add routes after `/api/summarize_chat`, currently ending at `backend/app.py:2063`)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: `generate_document_structure(prompt, language)` and `_build_docx`/`_build_pdf`/`_build_pptx`/`_build_xlsx` from Task 1/2.
- Produces: `POST /api/documents/generate` → `{"download_url": str, "filename": str}` (200) or `{"error": str}` (400/500). `GET /api/documents/download/<filename>` → the file (200, `as_attachment=True`) or `{"error": str}` (400/404).

- [ ] **Step 1: Ignore generated output**

Edit `.gitignore`. In the "Temporary Files" section (currently):
```
# ===================================================================
# Temporary Files
# ===================================================================
temp/
```
Change to:
```
# ===================================================================
# Temporary Files
# ===================================================================
temp/
generated_docs/
```

- [ ] **Step 2: Add the two routes**

In `backend/app.py`, immediately after the `summarize_chat` function ends (`backend/app.py:2063`, the blank line right before end of file section), add:
```python

GENERATED_DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'generated_docs')


@app.route('/api/documents/generate', methods=['POST'])
def generate_document():
    """Generate a downloadable Word/Excel/PDF/PowerPoint document from a chat prompt."""
    try:
        data = request.json or {}
        fmt = (data.get('format') or '').strip().lower()
        prompt = (data.get('prompt') or '').strip()
        language = _normalize_language_code(data.get('language', 'en'))

        allowed_formats = {'docx', 'xlsx', 'pdf', 'pptx'}
        if fmt not in allowed_formats:
            return jsonify({'error': f"format must be one of {sorted(allowed_formats)}"}), 400
        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400

        from services.document_generator import (
            generate_document_structure,
            _build_docx,
            _build_pdf,
            _build_pptx,
            _build_xlsx,
        )

        structure = generate_document_structure(prompt, language=language)
        if not structure or not structure.get('sections'):
            return jsonify({'error': 'Failed to generate document content'}), 500

        os.makedirs(GENERATED_DOCS_DIR, exist_ok=True)

        builders = {'docx': _build_docx, 'xlsx': _build_xlsx, 'pdf': _build_pdf, 'pptx': _build_pptx}
        subject_slug = _sanitize_filename_component(structure.get('title') or prompt)
        filename = f"{int(time.time())}-{subject_slug}.{fmt}"
        filepath = os.path.join(GENERATED_DOCS_DIR, filename)
        builders[fmt](structure, filepath)

        display_name = f"{structure.get('title') or prompt}.{fmt}"
        return jsonify({
            'download_url': f'/api/documents/download/{filename}',
            'filename': display_name,
        }), 200

    except Exception as e:
        logger.error(f"Document generation error: {e}", exc_info=True)
        return jsonify({'error': 'Failed to generate document'}), 500


@app.route('/api/documents/download/<path:filename>', methods=['GET'])
def download_document(filename):
    """Serve a previously generated document by filename."""
    safe_name = os.path.basename(filename)
    if safe_name != filename or safe_name in ('', '.', '..'):
        return jsonify({'error': 'Invalid filename'}), 400

    filepath = os.path.join(GENERATED_DOCS_DIR, safe_name)
    if not os.path.isfile(filepath):
        return jsonify({'error': 'File not found'}), 404

    return send_from_directory(GENERATED_DOCS_DIR, safe_name, as_attachment=True, download_name=safe_name)
```

- [ ] **Step 3: Add the filename sanitizer helper**

`_sanitize_filename_component` doesn't exist yet. Add it to `backend/services/document_generator.py` (it belongs next to the other text-processing helpers, since `app.py` has no `re` import and this keeps that import scoped to the module that already uses `re`):
```python
def _sanitize_filename_component(text):
    """Turn arbitrary text into a short, filesystem-safe slug."""
    cleaned = re.sub(r'[^\w\s-]', '', text or '').strip().lower()
    cleaned = re.sub(r'[\s]+', '-', cleaned)
    return cleaned[:60] or 'document'
```
Then in `backend/app.py`, update the import added in Step 2 to also pull in this helper:
```python
        from services.document_generator import (
            generate_document_structure,
            _build_docx,
            _build_pdf,
            _build_pptx,
            _build_xlsx,
            _sanitize_filename_component,
        )
```

- [ ] **Step 4: Restart the backend**

Run: `cd backend && python app.py`
Expected: server starts on port 5001 with no import errors (confirms the new routes registered and `services.document_generator` imports cleanly with the new dependencies from Task 1/2).

- [ ] **Step 5: Verify POST /api/documents/generate for all 4 formats**

Run (with the backend running, in a separate terminal), once per format:
```bash
curl -s -X POST http://localhost:5001/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"format":"docx","prompt":"the water cycle","language":"en"}'
curl -s -X POST http://localhost:5001/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"format":"pdf","prompt":"the water cycle","language":"en"}'
curl -s -X POST http://localhost:5001/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"format":"pptx","prompt":"the water cycle","language":"en"}'
curl -s -X POST http://localhost:5001/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"format":"xlsx","prompt":"top 3 planets by size","language":"en"}'
```
Expected: each returns `200` with JSON `{"download_url": "/api/documents/download/...", "filename": "..."}`.

- [ ] **Step 6: Verify GET /api/documents/download/<filename> serves a real file**

Using one `download_url` from Step 5's docx response:
```bash
curl -s -o /tmp/out.docx -w "%{http_code} %{size_download}\n" \
  http://localhost:5001/api/documents/download/<filename-from-step-5>
```
Expected: `200 <nonzero-byte-count>`. Confirm it's a real docx: `python -c "from docx import Document; print(Document('/tmp/out.docx').paragraphs[0].text)"` should print the generated title.

- [ ] **Step 7: Verify path-traversal and missing-file protection**

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:5001/api/documents/download/..%2f..%2fapp.py"
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:5001/api/documents/download/does-not-exist.docx"
```
Expected: first returns `400` (or `404` if Flask's `<path:filename>` converter already collapses the traversal before it reaches the handler — either is acceptable as long as `app.py` is never served), second returns `404`.

- [ ] **Step 8: Commit**

```bash
git add backend/app.py backend/services/document_generator.py .gitignore
git commit -m "feat: add /api/documents/generate and /api/documents/download routes"
```

---

### Task 4: Frontend API client — generateDocument()

**Files:**
- Modify: `chatbot-ui-vite/src/api/api.js` (add after `generateAIImage`, currently ending at `chatbot-ui-vite/src/api/api.js:327`)

**Interfaces:**
- Produces: `generateDocument({ format, prompt, language = "en" }) -> Promise<{ download_url: string, filename: string }>`. Used by Tasks 5-7.

- [ ] **Step 1: Add generateDocument**

In `chatbot-ui-vite/src/api/api.js`, immediately after the `generateAIImage` function (ends at line 327), add:
```js
export const generateDocument = async ({ format, prompt, language = "en" }) => {
  let response;
  try {
    response = await fetch("/api/documents/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ format, prompt, language }),
    });
  } catch (err) {
    throw new Error("Cannot reach backend. Start/restart backend server on port 5001.");
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Document API not found. Restart backend to load the new /api/documents/generate route.");
    }
    throw new Error(data?.error || "Document generation failed.");
  }
  return data;
};
```

- [ ] **Step 2: Verify it builds**

Run: `cd chatbot-ui-vite && npm run build`
Expected: build succeeds with no new errors.

- [ ] **Step 3: Commit**

```bash
git add chatbot-ui-vite/src/api/api.js
git commit -m "feat: add generateDocument API client"
```

---

### Task 5: Wire document detection into ChatWindow.jsx

**Files:**
- Modify: `chatbot-ui-vite/src/components/chat/ChatWindow.jsx`

**Interfaces:**
- Consumes: `generateDocument` from Task 4.
- Produces: `DOCUMENT_REQUEST_RE`, `extractDocumentRequest(text) -> { format: "docx"|"xlsx"|"pdf"|"pptx", subject: string } | null` — this exact shape and null-return-when-no-match contract is relied on identically in Tasks 6 and 7.

- [ ] **Step 1: Add the import**

In `chatbot-ui-vite/src/components/chat/ChatWindow.jsx:3`, change:
```js
import { generateAIImage, sendOrchestratedMessageStream, summarizeChat } from "../../api/api";
```
to:
```js
import { generateAIImage, generateDocument, sendOrchestratedMessageStream, summarizeChat } from "../../api/api";
```

- [ ] **Step 2: Add the detection regex and helper**

In `chatbot-ui-vite/src/components/chat/ChatWindow.jsx`, immediately after the existing `IMAGE_REQUEST_RE` / `extractImagePrompt` block (lines 7-15), add:
```js
const DOCUMENT_VERB_RE = /\b(create|generate|make|write|draft)\b.*\b(word\s*doc(ument)?|report|excel\s*(sheet|spreadsheet)|spreadsheet|pdf|power\s*point|presentation|slides?)\b/i;

const DOCUMENT_FORMAT_PATTERNS = [
  { format: "pptx", re: /power\s*point|presentation|slides?/i },
  { format: "xlsx", re: /excel|spreadsheet|sheet/i },
  { format: "pdf", re: /\bpdf\b/i },
  { format: "docx", re: /word\s*doc(ument)?|\bdoc(ument)?\b|report/i },
];

const extractDocumentRequest = (text) => {
  const raw = (text || "").trim();
  if (!raw || !DOCUMENT_VERB_RE.test(raw)) return null;
  const match = DOCUMENT_FORMAT_PATTERNS.find((p) => p.re.test(raw));
  if (!match) return null;
  const subject = raw
    .replace(/^(please\s+)?(create|generate|make|write|draft)\s+(an?\s+)?(ms\s*)?(word\s*doc(ument)?|excel\s*(sheet|spreadsheet)|spreadsheet|pdf|power\s*point(\s*(presentation|deck))?|presentation|slides?|report)\s*(about|on|for|regarding)?\s*/i, "")
    .trim() || raw;
  return { format: match.format, subject };
};
```

- [ ] **Step 3: Handle the document request before the image check**

In `chatbot-ui-vite/src/components/chat/ChatWindow.jsx`, inside `sendSuggestionMessage`'s `try` block, immediately before `if (IMAGE_REQUEST_RE.test(suggestion)) {` (line 90), add:
```js
      const docRequest = extractDocumentRequest(suggestion);
      if (docRequest) {
        const docResult = await generateDocument({
          format: docRequest.format,
          prompt: docRequest.subject,
          language: normalizeLanguageCode(language),
        });

        setIsLoading(false);
        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m, idx) =>
                    idx === c.messages.length - 1
                      ? {
                          ...m,
                          text: "Generated document ready.",
                          isStreaming: false,
                          attachments: [
                            {
                              name: docResult.filename,
                              type: "document",
                              downloadUrl: docResult.download_url,
                              format: docRequest.format,
                            },
                          ],
                        }
                      : m
                  ),
                }
              : c
          )
        );
        return;
      }

      if (IMAGE_REQUEST_RE.test(suggestion)) {
```
(Note: this replaces the standalone `if (IMAGE_REQUEST_RE...` line with the doc-check block followed by the same image-check line, so the image check still runs unchanged right after.)

- [ ] **Step 4: Verify it builds and lints**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: both succeed with no new errors/warnings.

- [ ] **Step 5: Manual verification**

Start the dev server (`npm run dev` from `chatbot-ui-vite/`) and the backend, open the app, click a suggestion card or type a phrase like "make a word document about the solar system" as a suggestion-triggered send. Confirm the bot message shows "Generated document ready." — full attachment rendering is verified in Task 8; for now confirm no console error is thrown and network tab shows a `200` on `/api/documents/generate`.

- [ ] **Step 6: Commit**

```bash
git add chatbot-ui-vite/src/components/chat/ChatWindow.jsx
git commit -m "feat: detect document generation requests in ChatWindow suggestions"
```

---

### Task 6: Wire document detection into InputBar.jsx

**Files:**
- Modify: `chatbot-ui-vite/src/components/input/InputBar.jsx`

**Interfaces:**
- Consumes: `generateDocument` from Task 4; the same `DOCUMENT_REQUEST_RE`/`extractDocumentRequest` shape defined in Task 5 (duplicated here per this codebase's established per-file pattern).

- [ ] **Step 1: Add the import**

In `chatbot-ui-vite/src/components/input/InputBar.jsx:3`, change:
```js
import { generateAIImage, sendOrchestratedMessage, sendOrchestratedMessageStream, sendOrchestratedUploadMessage } from "../../api/api";
```
to:
```js
import { generateAIImage, generateDocument, sendOrchestratedMessage, sendOrchestratedMessageStream, sendOrchestratedUploadMessage } from "../../api/api";
```

- [ ] **Step 2: Add the detection regex and helper**

In `chatbot-ui-vite/src/components/input/InputBar.jsx`, immediately after the existing `IMAGE_REQUEST_RE` / `extractImagePrompt` block (lines 14-22), add:
```js
const DOCUMENT_VERB_RE = /\b(create|generate|make|write|draft)\b.*\b(word\s*doc(ument)?|report|excel\s*(sheet|spreadsheet)|spreadsheet|pdf|power\s*point|presentation|slides?)\b/i;

const DOCUMENT_FORMAT_PATTERNS = [
  { format: "pptx", re: /power\s*point|presentation|slides?/i },
  { format: "xlsx", re: /excel|spreadsheet|sheet/i },
  { format: "pdf", re: /\bpdf\b/i },
  { format: "docx", re: /word\s*doc(ument)?|\bdoc(ument)?\b|report/i },
];

const extractDocumentRequest = (text) => {
  const raw = (text || "").trim();
  if (!raw || !DOCUMENT_VERB_RE.test(raw)) return null;
  const match = DOCUMENT_FORMAT_PATTERNS.find((p) => p.re.test(raw));
  if (!match) return null;
  const subject = raw
    .replace(/^(please\s+)?(create|generate|make|write|draft)\s+(an?\s+)?(ms\s*)?(word\s*doc(ument)?|excel\s*(sheet|spreadsheet)|spreadsheet|pdf|power\s*point(\s*(presentation|deck))?|presentation|slides?|report)\s*(about|on|for|regarding)?\s*/i, "")
    .trim() || raw;
  return { format: match.format, subject };
};
```

- [ ] **Step 3: Handle the document request before the image check**

In `chatbot-ui-vite/src/components/input/InputBar.jsx`, inside `handleSendMessage`'s `try` block, immediately before the line `const isImageRequest = IMAGE_REQUEST_RE.test(msgText) && msgAttachments.length === 0;` (line 178), add:
```js
      const docRequest = msgAttachments.length === 0 ? extractDocumentRequest(msgText) : null;
      if (docRequest) {
        const docResult = await generateDocument({
          format: docRequest.format,
          prompt: docRequest.subject,
          language: normalizedLanguage,
        });

        setIsLoading(false);
        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m, idx) =>
                    idx === c.messages.length - 1
                      ? {
                          ...m,
                          text: "Generated document ready.",
                          isStreaming: false,
                          attachments: [
                            {
                              name: docResult.filename,
                              type: "document",
                              downloadUrl: docResult.download_url,
                              format: docRequest.format,
                            },
                          ],
                        }
                      : m
                  ),
                }
              : c
          )
        );
        return;
      }

      const isImageRequest = IMAGE_REQUEST_RE.test(msgText) && msgAttachments.length === 0;
```
(Note: `normalizedLanguage` is already defined one line above this insertion point at line 177 — reuse it rather than recomputing.)

- [ ] **Step 4: Verify it builds and lints**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: both succeed with no new errors/warnings.

- [ ] **Step 5: Manual verification**

With dev server and backend running, type "generate a pdf report on climate change" into the chat input and send. Confirm network tab shows `200` on `/api/documents/generate` and the bot message reads "Generated document ready."

- [ ] **Step 6: Commit**

```bash
git add chatbot-ui-vite/src/components/input/InputBar.jsx
git commit -m "feat: detect document generation requests in InputBar"
```

---

### Task 7: Wire document detection into pragna/App.jsx

**Files:**
- Modify: `chatbot-ui-vite/src/pragna/App.jsx`

**Interfaces:**
- Consumes: `generateDocument` from Task 4; the same `DOCUMENT_REQUEST_RE`/`extractDocumentRequest` shape from Tasks 5-6.

- [ ] **Step 1: Add the import**

In `chatbot-ui-vite/src/pragna/App.jsx:3`, change:
```js
import { generateAIImage, sendOrchestratedMessageStream } from '../api/api'
```
to:
```js
import { generateAIImage, generateDocument, sendOrchestratedMessageStream } from '../api/api'
```

- [ ] **Step 2: Add the detection regex and helper**

In `chatbot-ui-vite/src/pragna/App.jsx`, immediately after the existing `IMAGE_REQUEST_RE` / `extractImagePrompt` block (lines 17-25), add:
```js
const DOCUMENT_VERB_RE = /\b(create|generate|make|write|draft)\b.*\b(word\s*doc(ument)?|report|excel\s*(sheet|spreadsheet)|spreadsheet|pdf|power\s*point|presentation|slides?)\b/i

const DOCUMENT_FORMAT_PATTERNS = [
  { format: 'pptx', re: /power\s*point|presentation|slides?/i },
  { format: 'xlsx', re: /excel|spreadsheet|sheet/i },
  { format: 'pdf', re: /\bpdf\b/i },
  { format: 'docx', re: /word\s*doc(ument)?|\bdoc(ument)?\b|report/i },
]

const extractDocumentRequest = (text) => {
  const raw = (text || '').trim()
  if (!raw || !DOCUMENT_VERB_RE.test(raw)) return null
  const match = DOCUMENT_FORMAT_PATTERNS.find((p) => p.re.test(raw))
  if (!match) return null
  const subject = raw
    .replace(/^(please\s+)?(create|generate|make|write|draft)\s+(an?\s+)?(ms\s*)?(word\s*doc(ument)?|excel\s*(sheet|spreadsheet)|spreadsheet|pdf|power\s*point(\s*(presentation|deck))?|presentation|slides?|report)\s*(about|on|for|regarding)?\s*/i, '')
    .trim() || raw
  return { format: match.format, subject }
}
```

- [ ] **Step 3: Handle the document request before the image check**

In `chatbot-ui-vite/src/pragna/App.jsx`, inside `sendQuickPrompt`'s `try` block, immediately before `if (IMAGE_REQUEST_RE.test(prompt)) {` (line 93), add:
```js
      const docRequest = extractDocumentRequest(prompt)
      if (docRequest) {
        const docResult = await generateDocument({
          format: docRequest.format,
          prompt: docRequest.subject,
          language: normalizeLanguageCode(language),
        })

        setIsLoading(false)
        setChats((prev) =>
          prev.map((c) =>
            c.id === targetChatId
              ? {
                  ...c,
                  messages: c.messages.map((m, idx) =>
                    idx === c.messages.length - 1
                      ? {
                          ...m,
                          text: 'Generated document ready.',
                          isStreaming: false,
                          attachments: [
                            {
                              name: docResult.filename,
                              type: 'document',
                              downloadUrl: docResult.download_url,
                              format: docRequest.format,
                            },
                          ],
                        }
                      : m
                  ),
                }
              : c
          )
        )
        return
      }

      if (IMAGE_REQUEST_RE.test(prompt)) {
```

- [ ] **Step 4: Verify it builds and lints**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: both succeed with no new errors/warnings.

- [ ] **Step 5: Manual verification**

With dev server and backend running, use a Home page quick prompt or type "create a powerpoint presentation about renewable energy" via `sendQuickPrompt`'s entry point. Confirm network tab shows `200` on `/api/documents/generate`.

- [ ] **Step 6: Commit**

```bash
git add chatbot-ui-vite/src/pragna/App.jsx
git commit -m "feat: detect document generation requests in quick prompts"
```

---

### Task 8: Render downloadable document attachments in MessageBubble.jsx

**Files:**
- Modify: `chatbot-ui-vite/src/components/chat/MessageBubble.jsx:284-322` (`renderAttachments`)

**Interfaces:**
- Consumes: `attachments` array entries of shape `{ type: "document", name: string, downloadUrl: string, format: "docx"|"xlsx"|"pdf"|"pptx" }` produced by Tasks 5-7.

- [ ] **Step 1: Add the document branch**

In `chatbot-ui-vite/src/components/chat/MessageBubble.jsx`, the `renderAttachments` function currently checks `att.type === "image"`, then `att.type === "video"`, then falls through to a decorative `else` for everything else (lines 284-322). Insert a new branch between the `"video"` branch and the final `else`:

Before (lines 297-319):
```js
      } else if (att.type === "video") {
        return (
          <div key={i} className="msg-attachment-file">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="2" y="5" width="15" height="14" rx="2"/>
              <path d="M17 9l5-3v12l-5-3V9z"/>
            </svg>
            <span>{att.name}</span>
          </div>
        );
      } else {
        return (
          <div key={i} className="msg-attachment-file">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="9" y1="13" x2="15" y2="13"/>
              <line x1="9" y1="17" x2="13" y2="17"/>
            </svg>
            <span>{att.name}</span>
          </div>
        );
      }
```

After:
```js
      } else if (att.type === "video") {
        return (
          <div key={i} className="msg-attachment-file">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="2" y="5" width="15" height="14" rx="2"/>
              <path d="M17 9l5-3v12l-5-3V9z"/>
            </svg>
            <span>{att.name}</span>
          </div>
        );
      } else if (att.type === "document") {
        return (
          <a
            key={i}
            href={att.downloadUrl}
            download={att.name}
            className="msg-attachment-file"
            style={{ textDecoration: "none" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="9" y1="13" x2="15" y2="13"/>
              <line x1="9" y1="17" x2="13" y2="17"/>
            </svg>
            <span>{att.name}</span>
            <span style={{ fontSize: "10px", opacity: 0.7, marginLeft: "4px" }}>
              {(att.format || "doc").toUpperCase()}
            </span>
          </a>
        );
      } else {
        return (
          <div key={i} className="msg-attachment-file">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="9" y1="13" x2="15" y2="13"/>
              <line x1="9" y1="17" x2="13" y2="17"/>
            </svg>
            <span>{att.name}</span>
          </div>
        );
      }
```

- [ ] **Step 2: Verify it builds and lints**

Run: `cd chatbot-ui-vite && npm run build && npm run lint`
Expected: both succeed with no new errors/warnings.

- [ ] **Step 3: End-to-end manual verification**

With dev server and backend running:
1. Type "make a word document about the water cycle" in the chat input and send.
2. Confirm the bot message renders a clickable attachment box showing the filename and a "DOCX" badge.
3. Click it — confirm a `.docx` file downloads and opens correctly in Word (or `python -c "from docx import Document; print(Document('<downloaded-file>').paragraphs[0].text)"` if Word isn't available) with sensible generated content.
4. Repeat steps 1-3 for a PDF ("create a pdf report on ocean pollution"), a PowerPoint ("generate a powerpoint presentation about ancient Rome"), and an Excel sheet ("make an excel spreadsheet comparing the top 5 programming languages"), confirming each downloads and opens as a valid file of the right type.
5. Confirm a normal chat message (no document phrase) and an existing image-generation request ("generate an ai image of a sunset") still behave exactly as before — no regression.

- [ ] **Step 4: Commit**

```bash
git add chatbot-ui-vite/src/components/chat/MessageBubble.jsx
git commit -m "feat: render downloadable document attachments in chat"
```
