import { useState } from "react";
import { useTranslation } from "react-i18next";
import { pick } from "../lib/lang";
import type { GeneratedExercise } from "../lib/types";
import { useGenerateExerciseMutation } from "../store/api";
import MultipleChoice from "./exercises/MultipleChoice";

/** Generates an extra multiple-choice practice question with the local LLM.
 * Checked locally (it's ephemeral practice, not stored as an attempt). */
export default function AiExtraExercise({ courseSlug }: { courseSlug: string }) {
  const { t, i18n } = useTranslation();
  const [generate, { isLoading }] = useGenerateExerciseMutation();
  const [exercise, setExercise] = useState<GeneratedExercise | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [checked, setChecked] = useState(false);
  const [error, setError] = useState(false);

  const run = async () => {
    setError(false);
    setChecked(false);
    setSelected([]);
    try {
      const res = await generate({ course_slug: courseSlug }).unwrap();
      setExercise(res);
    } catch {
      setError(true);
    }
  };

  const correct = exercise != null && selected.length > 0 && selected[0] === exercise.correct;

  return (
    <div className="card mt-6 p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
            <path d="M12 3v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1M5.6 18.4l2.1-2.1m8.6-8.6 2.1-2.1" />
          </svg>
          {t("generateExercise")}
        </h2>
        <button className="btn" onClick={run} disabled={isLoading}>
          {isLoading ? t("generating") : t("generateExercise")}
        </button>
      </div>
      {error && <p className="mt-3 text-sm text-warning">{t("aiUnavailable")}</p>}
      {exercise && (
        <div className="mt-4">
          <p className="mb-3 text-base">{pick(exercise.prompt, i18n.language)}</p>
          <MultipleChoice
            options={exercise.options}
            selected={selected}
            onChange={(s) => {
              setSelected(s);
              setChecked(false);
            }}
            disabled={checked && correct}
            correctIndexes={checked ? [exercise.correct] : null}
          />
          <div className="mt-3 flex items-center gap-3">
            <button
              className="btn btn-primary"
              onClick={() => setChecked(true)}
              disabled={selected.length === 0}
            >
              {t("check")}
            </button>
            {checked && (
              <span
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                  correct ? "bg-success-soft text-success" : "bg-error-soft text-error"
                }`}
              >
                {correct ? t("correct") : t("incorrect")}
              </span>
            )}
          </div>
          {checked && exercise.explanation && (
            <div className="mt-3 rounded-lg border border-border bg-surface2 px-4 py-3 text-sm">
              {pick(exercise.explanation, i18n.language)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
