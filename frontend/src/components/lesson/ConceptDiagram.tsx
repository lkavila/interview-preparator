import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { pick } from "../../lib/lang";
import type { LessonComponentConfig } from "../../lib/types";
import { Skeleton } from "./Skeleton";

interface ConceptDiagramProps {
  config: LessonComponentConfig;
}

let mermaidCounter = 0;

/** Renders a concept diagram: mermaid for flows/architectures, recharts for
 * numeric comparisons. Mermaid is imported lazily to keep the bundle small. */
export default function ConceptDiagram({ config }: ConceptDiagramProps) {
  const { t, i18n } = useTranslation();
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const isMermaid = config.kind !== "chart" && !!config.code;

  useEffect(() => {
    if (!isMermaid || !config.code) return;
    let cancelled = false;
    setSvg(null);
    setError(false);

    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        const dark = document.documentElement.classList.contains("dark");
        mermaid.initialize({
          startOnLoad: false,
          theme: dark ? "dark" : "neutral",
          fontFamily: "Inter, sans-serif",
          securityLevel: "strict",
        });
        const { svg: rendered } = await mermaid.render(
          `concept-diagram-${++mermaidCounter}`,
          config.code!
        );
        if (!cancelled) setSvg(rendered);
      } catch {
        if (!cancelled) setError(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [config.code, isMermaid]);

  if (error) return null;

  return (
    <section className="card p-5" aria-label={t("conceptDiagram")}>
      <h2 className="mb-3 text-[12px] font-medium uppercase tracking-wider text-muted">
        🗺️ {t("conceptDiagram")}
      </h2>

      {isMermaid ? (
        svg ? (
          <div
            ref={containerRef}
            className="overflow-x-auto [&_svg]:mx-auto [&_svg]:max-w-full"
            role="img"
            aria-label={config.caption ? pick(config.caption, i18n.language) : t("conceptDiagram")}
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        ) : (
          <Skeleton className="h-48 w-full" />
        )
      ) : config.chart ? (
        <div className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            {config.chart.type === "line" ? (
              <LineChart data={config.chart.data}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
                <YAxis stroke="var(--text-muted)" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    color: "var(--text)",
                  }}
                />
                <Line type="monotone" dataKey="value" stroke="var(--accent)" dot={false} />
              </LineChart>
            ) : (
              <BarChart data={config.chart.data}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
                <YAxis stroke="var(--text-muted)" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    color: "var(--text)",
                  }}
                />
                <Bar dataKey="value" fill="var(--accent)" radius={[4, 4, 0, 0]} />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      ) : null}

      {config.caption && (
        <p className="mt-3 text-center text-[12.5px] text-muted">
          {pick(config.caption, i18n.language)}
        </p>
      )}
    </section>
  );
}
