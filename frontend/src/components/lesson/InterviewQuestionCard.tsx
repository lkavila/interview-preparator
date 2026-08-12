import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { EnrichmentInterviewQuestion } from "../../lib/types";

interface InterviewQuestionCardProps {
  questions: EnrichmentInterviewQuestion[];
  source: "llm" | "fallback";
}

/** Real interview questions about the lesson topic, each with a collapsible
 * LLM-suggested answer. */
export default function InterviewQuestionCard({ questions, source }: InterviewQuestionCardProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<Set<number>>(new Set());

  if (questions.length === 0) return null;

  const toggle = (i: number) => {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  return (
    <section className="card p-5" aria-label={t("realInterviewQuestions")}>
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-[12px] font-medium uppercase tracking-wider text-muted">
          {t("realInterviewQuestions")}
        </h2>
        <span className="rounded bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent">
          {source === "llm" ? t("aiGenerated") : t("fallbackContent")}
        </span>
      </div>
      <ul className="space-y-3">
        {questions.map((q, i) => {
          const expanded = open.has(i);
          return (
            <li key={i} className="rounded-lg border border-border bg-surface2/50 p-4">
              <p className="text-[14px] font-medium">
                <span aria-hidden="true" className="mr-1.5">💬</span>
                {q.question}
              </p>
              <button
                className="mt-2 text-[13px] font-medium text-accent hover:underline"
                onClick={() => toggle(i)}
                aria-expanded={expanded}
              >
                {expanded ? t("hideSuggestedAnswer") : t("showSuggestedAnswer")}
              </button>
              <AnimatePresence initial={false}>
                {expanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="mt-2 rounded-md border border-border bg-surface px-3 py-2.5 text-[13.5px] leading-relaxed text-muted">
                      {q.suggested_answer}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
