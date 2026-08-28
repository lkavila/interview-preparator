import { useTranslation } from "react-i18next";
import { pick } from "../../lib/lang";
import type { Bilingual } from "../../lib/types";

interface Props {
  options: Bilingual[];
  multiple?: boolean;
  selected: number[];
  onChange: (selected: number[]) => void;
  disabled?: boolean;
  correctIndexes?: number[] | null; // revealed after attempt
}

export default function MultipleChoice({
  options,
  multiple,
  selected,
  onChange,
  disabled,
  correctIndexes,
}: Props) {
  const { t, i18n } = useTranslation();

  const toggle = (i: number) => {
    if (disabled) return;
    if (multiple) {
      onChange(selected.includes(i) ? selected.filter((x) => x !== i) : [...selected, i]);
    } else {
      onChange([i]);
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted">{multiple ? t("selectAll") : t("selectAnswer")}</p>
      {options.map((opt, i) => {
        const isSelected = selected.includes(i);
        const revealed = correctIndexes != null;
        const isCorrect = revealed && correctIndexes!.includes(i);
        const isWrongPick = revealed && isSelected && !isCorrect;
        return (
          <button
            key={i}
            type="button"
            onClick={() => toggle(i)}
            disabled={disabled}
            className={`flex w-full items-start gap-3 rounded-lg border px-3.5 py-2.5 text-left text-base transition-colors ${
              isCorrect
                ? "border-success bg-success-soft"
                : isWrongPick
                  ? "border-error bg-error-soft"
                  : isSelected
                    ? "border-accent bg-accent-soft"
                    : "border-border bg-surface hover:bg-surface2"
            } ${disabled ? "cursor-default" : "cursor-pointer"}`}
          >
            <span
              className={`mt-0.5 flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full border text-2xs font-semibold ${
                isSelected ? "border-accent text-accent" : "border-border text-muted"
              }`}
              style={{ width: 18, height: 18 }}
            >
              {String.fromCharCode(65 + i)}
            </span>
            <span>{pick(opt, i18n.language)}</span>
          </button>
        );
      })}
    </div>
  );
}
