import type { Bilingual } from "./types";

export function pick(value: Bilingual | undefined | null, lang: string): string {
  if (!value) return "";
  return (lang === "es" ? value.es : value.en) || value.en || value.es || "";
}

export function formatDuration(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = Math.floor(totalSeconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s.toString().padStart(2, "0")}s`;
  return `${s}s`;
}

/** Minimal markdown renderer for lesson content (bold, code, lists, headings). */
export function renderMarkdown(md: string): string {
  const escapeHtml = (s: string) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const blocks = md.split(/```/);
  let html = "";
  blocks.forEach((block, i) => {
    if (i % 2 === 1) {
      const firstNewline = block.indexOf("\n");
      const code = firstNewline >= 0 ? block.slice(firstNewline + 1) : block;
      html += `<pre><code>${escapeHtml(code.trimEnd())}</code></pre>`;
      return;
    }
    const lines = escapeHtml(block).split("\n");
    let inList = false;
    let listTag = "ul";
    for (const line of lines) {
      const olMatch = /^\s*\d+\.\s+(.*)/.exec(line);
      const ulMatch = /^\s*[-*]\s+(.*)/.exec(line);
      if (ulMatch || olMatch) {
        const tag = olMatch ? "ol" : "ul";
        if (!inList || listTag !== tag) {
          if (inList) html += `</${listTag}>`;
          html += `<${tag}>`;
          inList = true;
          listTag = tag;
        }
        html += `<li>${inline((ulMatch || olMatch)![1])}</li>`;
        continue;
      }
      if (inList) {
        html += `</${listTag}>`;
        inList = false;
      }
      const h = /^(#{1,3})\s+(.*)/.exec(line);
      if (h) {
        const level = h[1].length + 2; // h3..h5 sizes
        html += `<h${Math.min(level, 6)}>${inline(h[2])}</h${Math.min(level, 6)}>`;
      } else if (line.trim() === "") {
        // skip
      } else {
        html += `<p>${inline(line)}</p>`;
      }
    }
    if (inList) html += `</${listTag}>`;
  });
  return html;

  function inline(s: string): string {
    return s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  }
}
