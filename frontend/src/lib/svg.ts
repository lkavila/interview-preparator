/** Allow-list sanitiser for the inline figures that ship with spatial-reasoning
 * questions.
 *
 * The SVG is first-party (it comes from the seed files, which are validated at
 * authoring time), but it is injected into the DOM, so it is parsed and rebuilt
 * against an explicit allow-list on the way in. An allow-list this small does
 * not justify pulling in a sanitiser dependency.
 */

const ALLOWED_TAGS = new Set([
  "svg",
  "g",
  "path",
  "rect",
  "circle",
  "ellipse",
  "line",
  "polyline",
  "polygon",
  "text",
  "tspan",
  "defs",
  "marker",
  "title",
  "desc",
]);

const ALLOWED_ATTRS = new Set([
  "viewbox",
  "xmlns",
  "class",
  "transform",
  "d",
  "x",
  "y",
  "x1",
  "y1",
  "x2",
  "y2",
  "cx",
  "cy",
  "r",
  "rx",
  "ry",
  "width",
  "height",
  "points",
  "fill",
  "fill-opacity",
  "fill-rule",
  "stroke",
  "stroke-width",
  "stroke-linecap",
  "stroke-linejoin",
  "stroke-dasharray",
  "stroke-opacity",
  "opacity",
  "font-size",
  "font-family",
  "font-weight",
  "text-anchor",
  "dominant-baseline",
  "dy",
  "dx",
  "marker-end",
  "id",
  "orient",
  "refx",
  "refy",
  "markerwidth",
  "markerheight",
]);

function scrub(node: Element): void {
  for (const child of Array.from(node.children)) {
    if (!ALLOWED_TAGS.has(child.tagName.toLowerCase())) {
      child.remove();
      continue;
    }
    for (const attr of Array.from(child.attributes)) {
      // Drops every on* handler and every href/xlink:href along with it.
      if (!ALLOWED_ATTRS.has(attr.name.toLowerCase())) child.removeAttribute(attr.name);
    }
    scrub(child);
  }
}

/** Returns sanitised SVG markup, or "" when the input is not usable SVG. */
export function sanitizeSvg(raw: string | null | undefined): string {
  if (!raw) return "";
  const doc = new DOMParser().parseFromString(raw, "image/svg+xml");
  if (doc.querySelector("parsererror")) return "";

  const root = doc.documentElement;
  if (!root || root.tagName.toLowerCase() !== "svg") return "";

  for (const attr of Array.from(root.attributes)) {
    if (!ALLOWED_ATTRS.has(attr.name.toLowerCase())) root.removeAttribute(attr.name);
  }
  scrub(root);

  // Let the figure scale with its container instead of its authored size.
  root.removeAttribute("width");
  root.removeAttribute("height");
  return root.outerHTML;
}
