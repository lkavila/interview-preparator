import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { sanitizeSvg } from "../../lib/svg";

interface Props {
  /** Exam questions carry the figure in a column; lesson exercises in `data`. */
  svg: string | null | undefined;
  label?: string;
}

/** Renders the inline figure of a spatial-reasoning question.
 *
 * Wrapped the same way as ConceptDiagram: horizontally scrollable on narrow
 * screens and announced as a single image to screen readers. */
export default function QuestionFigure({ svg, label }: Props) {
  const { t } = useTranslation();
  const clean = useMemo(() => sanitizeSvg(svg), [svg]);
  if (!clean) return null;

  return (
    <div
      className="scroll-x mb-4 rounded-lg border border-border bg-surface2 px-4 py-4 text-text [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:w-full [&_svg]:max-w-xs"
      role="img"
      aria-label={label ?? t("questionFigure")}
      dangerouslySetInnerHTML={{ __html: clean }}
    />
  );
}
