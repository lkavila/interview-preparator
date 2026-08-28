import { useTranslation } from "react-i18next";

export interface TableColumn {
  name: string;
  type: string;
}

interface Props {
  columns: TableColumn[];
  onChange: (columns: TableColumn[]) => void;
  typeOptions?: string[];
  disabled?: boolean;
}

const DEFAULT_TYPES = [
  "SERIAL",
  "INTEGER",
  "BIGINT",
  "NUMERIC",
  "TEXT",
  "VARCHAR(255)",
  "BOOLEAN",
  "DATE",
  "TIMESTAMP",
  "TIMESTAMPTZ",
  "JSONB",
  "UUID",
];

/** Build a table schema by adding columns with a name and a type. */
export default function TableBuilder({ columns, onChange, typeOptions, disabled }: Props) {
  const { t } = useTranslation();
  const types = typeOptions ?? DEFAULT_TYPES;

  const update = (i: number, patch: Partial<TableColumn>) => {
    onChange(columns.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));
  };

  return (
    <div className="space-y-2">
      {/* The three columns need a real minimum width to stay usable; below that
          the row scrolls sideways rather than squeezing the inputs to nothing. */}
      <div className="scroll-x rounded-lg border border-border">
        <div className="min-w-[380px]">
        <div className="grid grid-cols-[1fr_1fr_36px] gap-0 border-b border-border bg-surface2 px-3 py-1.5 text-xs font-medium text-muted">
          <span>{t("columnName")}</span>
          <span>{t("columnType")}</span>
          <span />
        </div>
        {columns.length === 0 && (
          <p className="px-3 py-3 text-center text-sm text-muted">—</p>
        )}
        {columns.map((col, i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_1fr_36px] items-center gap-2 border-b border-border px-3 py-1.5 last:border-b-0"
          >
            <input
              className="input !py-1 font-mono text-sm"
              value={col.name}
              placeholder="column_name"
              onChange={(e) => update(i, { name: e.target.value })}
              disabled={disabled}
            />
            <select
              className="input !py-1 font-mono text-sm"
              value={col.type}
              onChange={(e) => update(i, { type: e.target.value })}
              disabled={disabled}
            >
              <option value="">—</option>
              {types.map((ty) => (
                <option key={ty} value={ty}>
                  {ty}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="text-muted hover:text-error"
              onClick={() => onChange(columns.filter((_, idx) => idx !== i))}
              disabled={disabled}
              title={t("remove")}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          </div>
        ))}
        </div>
      </div>
      {!disabled && (
        <button
          type="button"
          className="btn !py-1 text-xs"
          onClick={() => onChange([...columns, { name: "", type: "" }])}
        >
          + {t("addColumn")}
        </button>
      )}
    </div>
  );
}
