import { test } from "node:test";
import assert from "node:assert/strict";
import { extractDocument, MAX_FILE_BYTES, MAX_TEXT_CHARS } from "../../site/document-import.mjs";

const file = (text, name = "brief.txt") => new File([text], name);
const rejects = (promise, code) => assert.rejects(promise, error => error.code === code);

test("text above the old API limit is imported whole, including the tail", async () => {
  const text = "An expectation. ".repeat(40_000) + "FINAL REQUIREMENT";
  const result = await extractDocument(file(text));
  assert.equal(result.text, text);
  assert.equal(result.chars, text.length);
});

test("text limit is inclusive and counts Unicode like Python", async () => {
  assert.equal((await extractDocument(file("😀abc"), { maxChars: 4 })).chars, 4);
  await rejects(extractDocument(file("😀abcd"), { maxChars: 4 }), "textLimit");
  assert.equal((await extractDocument(file("x".repeat(MAX_TEXT_CHARS)))).chars, MAX_TEXT_CHARS);
  await rejects(extractDocument(file("x".repeat(MAX_TEXT_CHARS + 1))), "textLimit");
});

test("oversized file is rejected before any bytes are read", async () => {
  await rejects(extractDocument({ name: "brief.pdf", size: MAX_FILE_BYTES + 1,
    arrayBuffer() { assert.fail("must reject before reading"); } }), "fileLimit");
});

test("unsupported, empty and invalid UTF-8 files get explicit errors", async () => {
  await rejects(extractDocument(file("text", "brief.docx")), "format");
  await rejects(extractDocument(file(" \n")), "empty");
  await rejects(extractDocument(new File([new Uint8Array([255, 254])], "brief.txt")), "encoding");
});

function pdfLoader(pages, state) {
  return async () => ({ getDocument(options) {
    assert.equal(options.isEvalSupported, false);
    assert.equal(options.stopAtErrors, true);
    return {
      destroy: async () => { state.destroyed = true; },
      promise: Promise.resolve({ numPages: pages.length, getPage: async n => ({
        cleanup() {},
        getTextContent: async () => ({ items: [{ str: pages[n - 1], hasEOL: true }] }),
      }) }),
    };
  } });
}

test("a PDF of exactly 10 MB is accepted and all pages are extracted in order", async () => {
  const state = {};
  const input = { name: "brief.pdf", size: MAX_FILE_BYTES, arrayBuffer: async () => new ArrayBuffer(1) };
  const result = await extractDocument(input, { pdfLoader: pdfLoader(["first", "last"], state) });
  assert.equal(result.text, "first\n\n\nlast\n");
  assert.equal(result.pages, 2);
  assert.equal(state.destroyed, true);
});

test("a scanned page or expanded text limit refuses the whole PDF and cleans up", async () => {
  for (const [pages, code] of [[["first", ""], "scanned"], [["first", "last"], "textLimit"]]) {
    const state = {};
    await rejects(extractDocument(file("pdf", "brief.pdf"), { pdfLoader: pdfLoader(pages, state), maxChars: 7 }), code);
    assert.equal(state.destroyed, true);
  }
});

test("a stalled parser is stopped, rather than leaving a worker running", async () => {
  let destroyed = false;
  const loader = async () => ({ getDocument: () => ({
    promise: new Promise(() => {}), destroy: async () => { destroyed = true; },
  }) });
  await rejects(extractDocument(file("pdf", "brief.pdf"), { pdfLoader: loader, timeoutMs: 5 }), "timeout");
  assert.equal(destroyed, true);
});

function syntheticPdf(text) {
  const stream = `BT /F1 12 Tf 40 700 Td (${text}) Tj ET`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  for (let i = 0; i < objects.length; i++) {
    offsets.push(pdf.length);
    pdf += `${i + 1} 0 obj\n${objects[i]}\nendobj\n`;
  }
  const xref = pdf.length;
  pdf += `xref\n0 6\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1)) pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  return pdf + `trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
}

test("vendored PDF.js extracts an actual PDF at the 10 MB file boundary", async () => {
  const pdf = syntheticPdf("A verifiable final requirement.").padEnd(MAX_FILE_BYTES, " ");
  const result = await extractDocument(file(pdf, "brief.pdf"));
  assert.equal(result.pages, 1);
  assert.equal(result.text.trim(), "A verifiable final requirement.");
});

test("vendored parser refuses a malformed PDF", async () => {
  await rejects(extractDocument(file("not a PDF", "brief.pdf")), "pdf");
});
