import { go } from "@codemirror/lang-go";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { sql } from "@codemirror/lang-sql";
import CodeMirror from "@uiw/react-codemirror";
import { useSelector } from "react-redux";
import type { RootState } from "../../store";

interface Props {
  language?: "javascript" | "typescript" | "python" | "sql" | "go";
  value: string;
  onChange: (code: string) => void;
  disabled?: boolean;
}

const EXTENSIONS = {
  python,
  sql,
  go,
  javascript: () => javascript({ typescript: true }),
  typescript: () => javascript({ typescript: true }),
};

export default function CodeExercise({ language, value, onChange, disabled }: Props) {
  const theme = useSelector((s: RootState) => s.auth.user?.theme ?? "dark");
  // Unknown languages fall back to the JS/TS grammar, which is close enough
  // for most C-like syntax to stay readable.
  const extension = (EXTENSIONS[language as keyof typeof EXTENSIONS] ?? EXTENSIONS.javascript)();

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <CodeMirror
        value={value}
        minHeight="140px"
        maxHeight="55vh"
        theme={theme === "dark" ? "dark" : "light"}
        extensions={[extension]}
        onChange={onChange}
        editable={!disabled}
        basicSetup={{ lineNumbers: true, foldGutter: false }}
      />
    </div>
  );
}
