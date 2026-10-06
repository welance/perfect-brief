// Files stay in the browser. Only reviewed text enters the existing score API.
export const MAX_FILE_BYTES = 10_000_000;
export const MAX_TEXT_CHARS = 1_000_000;

export class DocumentError extends Error {
  constructor(code) { super(code); this.code = code; }
}

function checkedText(text, maxChars) {
  let count = 0;
  for (const unused of text) { // Unicode code points, matching Python len().
    if (++count > maxChars) throw new DocumentError("textLimit");
  }
  if (!text.trim()) throw new DocumentError("empty");
  return { text, chars: count };
}

async function loadPdf() {
  const pdf = await import("./vendor/pdfjs/pdf.min.mjs");
  pdf.GlobalWorkerOptions.workerSrc = new URL("./vendor/pdfjs/pdf.worker.min.mjs", import.meta.url).href;
  return pdf;
}

export async function extractDocument(file, { maxChars = MAX_TEXT_CHARS, pdfLoader = loadPdf, timeoutMs = 60_000 } = {}) {
  if (file.size > MAX_FILE_BYTES) throw new DocumentError("fileLimit");
  const extension = file.name.split(".").pop().toLowerCase();
  if (!["pdf", "txt", "md"].includes(extension)) throw new DocumentError("format");
  if (extension !== "pdf") {
    let text;
    try { text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer()); }
    catch { throw new DocumentError("encoding"); }
    if (text.includes("\0")) throw new DocumentError("encoding");
    return { ...checkedText(text, maxChars), pages: null };
  }
  let task, timer, expired = false;
  try {
    return await Promise.race([
      (async () => {
        const pdf = await pdfLoader();
        const data = new Uint8Array(await file.arrayBuffer());
        if (expired) throw new DocumentError("timeout");
        task = pdf.getDocument({ data, isEvalSupported: false, useWorkerFetch: false, stopAtErrors: true });
        const doc = await task.promise;
        if (doc.numPages > 1000) throw new DocumentError("pagesLimit");
        const pages = [];
        let chars = 0;
        for (let n = 1; n <= doc.numPages; n++) {
          const page = await doc.getPage(n);
          const content = await page.getTextContent();
          const text = content.items.map(item => typeof item.str === "string" ? item.str + (item.hasEOL ? "\n" : " ") : "").join("");
          page.cleanup();
          // Do not silently score only the text-bearing pages of a scanned PDF.
          if (!text.trim()) throw new DocumentError("scanned");
          chars += checkedText(text, maxChars).chars + (n > 1 ? 2 : 0);
          if (chars > maxChars) throw new DocumentError("textLimit");
          pages.push(text);
        }
        return { text: pages.join("\n\n"), chars, pages: doc.numPages };
      })(),
      new Promise((_, reject) => {
        timer = setTimeout(() => { expired = true; reject(new DocumentError("timeout")); }, timeoutMs);
      }),
    ]);
  } catch (error) {
    if (error instanceof DocumentError) throw error;
    throw new DocumentError("pdf");
  } finally {
    clearTimeout(timer);
    if (task) await task.destroy();
  }
}

const COPY = {
  en: {
    label: "Import a document",
    hint: "PDF, TXT or Markdown · up to 10 MB. Extraction stays on your device. When you score with AI, the extracted text is sent to the service and model; evidence caching is disabled for imported documents.",
    reading: "Reading the document…",
    ready: (r) => `${r.chars.toLocaleString()} characters imported${r.pages ? ` from ${r.pages} pages` : ""}. Review the text, then score it.`,
    fileLimit: "The file exceeds 10 MB. Choose a smaller document.",
    textLimit: "The extracted text exceeds 1,000,000 characters. Choose a shorter document; nothing was truncated.",
    empty: "No text was found in this document.",
    format: "Choose a PDF, TXT or Markdown file.",
    encoding: "Choose a text file saved as UTF-8.",
    scanned: "At least one PDF page has no extractable text. Run OCR or remove blank pages before importing; no partial document was loaded.",
    pagesLimit: "This PDF exceeds 1,000 pages. Choose a shorter document.",
    timeout: "Extraction took too long. Choose a simpler or shorter PDF.",
    pdf: "This PDF could not be read. Check that it is valid and not password-protected.",
  },
  it: {
    label: "Importa un documento",
    hint: "PDF, TXT o Markdown · fino a 10 MB. Il testo viene estratto sul dispositivo. Quando valuti con l’AI, il testo estratto viene inviato al servizio e al modello; la cache delle evidenze è disattivata per i documenti importati.",
    reading: "Lettura del documento…",
    ready: (r) => `${r.chars.toLocaleString("it")} caratteri importati${r.pages ? ` da ${r.pages} pagine` : ""}. Controlla il testo, poi avvia la valutazione.`,
    fileLimit: "Il file supera 10 MB. Scegli un documento più piccolo.",
    textLimit: "Il testo estratto supera 1.000.000 di caratteri. Scegli un documento più breve; il testo non è stato troncato.",
    empty: "Il documento non contiene testo.",
    format: "Scegli un file PDF, TXT o Markdown.",
    encoding: "Scegli un file di testo salvato in UTF-8.",
    scanned: "Almeno una pagina del PDF non contiene testo estraibile. Esegui l’OCR o rimuovi le pagine vuote prima di importare; non è stato caricato un documento parziale.",
    pagesLimit: "Il PDF supera 1.000 pagine. Scegli un documento più breve.",
    timeout: "L’estrazione ha richiesto troppo tempo. Scegli un PDF più semplice o più breve.",
    pdf: "Impossibile leggere il PDF. Verifica che sia valido e non protetto da password.",
  },
};

if (typeof document !== "undefined") {
  const picker = document.getElementById("document-file");
  if (picker) {
    const input = document.getElementById("input");
    const status = document.getElementById("document-status");
    const copy = () => COPY[document.documentElement.lang.split("-")[0]] || COPY.en;
    const localise = () => {
      document.getElementById("document-label").textContent = copy().label;
      document.getElementById("document-hint").textContent = copy().hint;
    };
    localise();
    new MutationObserver(localise).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
    picker.addEventListener("change", async () => {
      const file = picker.files[0];
      if (!file) return;
      picker.disabled = true;
      input.readOnly = true;
      status.textContent = copy().reading;
      try {
        const result = await extractDocument(file);
        input.value = result.text;
        input.dataset.documentImport = "true";
        input.dispatchEvent(new Event("input", { bubbles: true }));
        status.textContent = copy().ready(result);
      } catch (error) {
        status.textContent = copy()[error.code] || copy().pdf;
      } finally {
        picker.disabled = false;
        picker.value = "";
        input.readOnly = false;
      }
    });
  }
}
