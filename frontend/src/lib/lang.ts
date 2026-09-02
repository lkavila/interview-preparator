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

/** Countdown clock as MM:SS, floored at zero. */
export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

/** Minimal markdown renderer for lesson content (bold, code, lists, headings,
 * and GFM-style tables). */
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
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // A table is a pipe row followed by a |---|---| separator row. Anything
      // else starting with a pipe is left alone and rendered as a paragraph.
      if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
        if (inList) {
          html += `</${listTag}>`;
          inList = false;
        }
        html += `<table><thead><tr>${cells(line).map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>`;
        i += 2;
        for (; i < lines.length && isTableRow(lines[i]); i++) {
          html += `<tr>${cells(lines[i]).map((c) => `<td>${c}</td>`).join("")}</tr>`;
        }
        i--; // the for-loop's i++ will land on the first non-row line
        html += "</tbody></table>";
        continue;
      }

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

  function isTableRow(s: string): boolean {
    return /^\s*\|.*\|\s*$/.test(s);
  }

  function isTableSeparator(s: string): boolean {
    return /^\s*\|(\s*:?-+:?\s*\|)+\s*$/.test(s);
  }

  function cells(row: string): string[] {
    return row
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((c) => inline(c.trim()));
  }
}
