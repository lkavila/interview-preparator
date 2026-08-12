import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { pick } from "../../lib/lang";
import type { Bilingual } from "../../lib/types";

interface Item {
  id: string;
  label: Bilingual;
}

interface Props {
  left: Item[];
  right: Item[];
  pairs: Record<string, string>;
  onChange: (pairs: Record<string, string>) => void;
  disabled?: boolean;
}

const LINE_COLORS = ["#7f9fd4", "#5aa984", "#c2a45c", "#c47878", "#9d7fd4", "#5aa9a9", "#c78fb0", "#8fa35a"];

/** Connect-the-concepts exercise: click a left item, then a right item to draw a line. */
export default function Matching({ left, right, pairs, onChange, disabled }: Props) {
  const { t, i18n } = useTranslation();
  const [activeLeft, setActiveLeft] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Map<string, HTMLButtonElement>>(new Map());
  const [lines, setLines] = useState<
    { x1: number; y1: number; x2: number; y2: number; color: string }[]
  >([]);
  const [shuffledRight] = useState(() => [...right].sort(() => Math.random() - 0.5));

  const setRef = (key: string) => (el: HTMLButtonElement | null) => {
    if (el) itemRefs.current.set(key, el);
    else itemRefs.current.delete(key);
  };

  const recomputeLines = () => {
    const container = containerRef.current;
    if (!container) return;
    const cRect = container.getBoundingClientRect();
    const next: typeof lines = [];
    Object.entries(pairs).forEach(([l, r]) => {
      const lEl = itemRefs.current.get(`L:${l}`);
      const rEl = itemRefs.current.get(`R:${r}`);
      if (!lEl || !rEl) return;
      const lRect = lEl.getBoundingClientRect();
      const rRect = rEl.getBoundingClientRect();
      const colorIdx = left.findIndex((item) => item.id === l);
      next.push({
        x1: lRect.right - cRect.left,
        y1: lRect.top + lRect.height / 2 - cRect.top,
        x2: rRect.left - cRect.left,
        y2: rRect.top + rRect.height / 2 - cRect.top,
        color: LINE_COLORS[colorIdx % LINE_COLORS.length],
      });
    });
    setLines(next);
  };

  useLayoutEffect(recomputeLines, [pairs, i18n.language]);
  useEffect(() => {
    window.addEventListener("resize", recomputeLines);
    return () => window.removeEventListener("resize", recomputeLines);
  });

  const clickLeft = (id: string) => {
    if (disabled) return;
    if (pairs[id]) {
      const next = { ...pairs };
      delete next[id];
      onChange(next);
      setActiveLeft(id);
      return;
    }
    setActiveLeft(activeLeft === id ? null : id);
  };

  const clickRight = (id: string) => {
    if (disabled) return;
    const owner = Object.keys(pairs).find((k) => pairs[k] === id);
    if (owner) {
      const next = { ...pairs };
      delete next[owner];
      onChange(next);
      return;
    }
    if (activeLeft) {
      onChange({ ...pairs, [activeLeft]: id });
      setActiveLeft(null);
    }
  };

  const usedRight = new Set(Object.values(pairs));

  return (
    <div>
      <p className="mb-2 text-[12.5px] text-muted">{t("matchInstruction")}</p>
      <div ref={containerRef} className="relative">
        <svg className="pointer-events-none absolute inset-0 h-full w-full" style={{ zIndex: 1 }}>
          {lines.map((l, i) => (
            <line
              key={i}
              x1={l.x1}
              y1={l.y1}
              x2={l.x2}
              y2={l.y2}
              stroke={l.color}
              strokeWidth="1.5"
              opacity="0.75"
            />
          ))}
        </svg>
        <div className="grid grid-cols-2 gap-x-14 gap-y-2">
          <div className="space-y-2">
            {left.map((item, idx) => {
              const paired = !!pairs[item.id];
              return (
                <button
                  key={item.id}
                  type="button"
                  ref={setRef(`L:${item.id}`)}
                  onClick={() => clickLeft(item.id)}
                  disabled={disabled}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-[13.5px] transition-colors ${
                    activeLeft === item.id
                      ? "border-accent bg-accent-soft"
                      : paired
                        ? "bg-surface2"
                        : "border-border bg-surface hover:bg-surface2"
                  }`}
                  style={paired ? { borderColor: LINE_COLORS[idx % LINE_COLORS.length] } : undefined}
                >
                  {pick(item.label, i18n.language)}
                </button>
              );
            })}
          </div>
          <div className="space-y-2">
            {shuffledRight.map((item) => {
              const paired = usedRight.has(item.id);
              const ownerIdx = left.findIndex((l) => pairs[l.id] === item.id);
              return (
                <button
                  key={item.id}
                  type="button"
                  ref={setRef(`R:${item.id}`)}
                  onClick={() => clickRight(item.id)}
                  disabled={disabled}
                  className={`w-full rounded-lg border px-3 py-2 text-left text-[13.5px] transition-colors ${
                    paired ? "bg-surface2" : "border-border bg-surface hover:bg-surface2"
                  }`}
                  style={
                    paired && ownerIdx >= 0
                      ? { borderColor: LINE_COLORS[ownerIdx % LINE_COLORS.length] }
                      : undefined
                  }
                >
                  {pick(item.label, i18n.language)}
                </button>
              );
            })}
          </div>
        </div>
      </div>
      {!disabled && Object.keys(pairs).length > 0 && (
        <button type="button" className="btn mt-3 !py-1 text-[12px]" onClick={() => onChange({})}>
          {t("clear")}
        </button>
      )}
    </div>
  );
}
