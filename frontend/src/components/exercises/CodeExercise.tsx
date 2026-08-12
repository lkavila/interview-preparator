import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { sql } from "@codemirror/lang-sql";
import CodeMirror from "@uiw/react-codemirror";
import { useSelector } from "react-redux";
import type { RootState } from "../../store";

interface Props {
  language?: "javascript" | "python" | "sql";
  value: string;
  onChange: (code: string) => void;
  disabled?: boolean;
}

export default function CodeExercise({ language, value, onChange, disabled }: Props) {
  const theme = useSelector((s: RootState) => s.auth.user?.theme ?? "dark");
  const extension =
    language === "python" ? python() : language === "sql" ? sql() : javascript({ typescript: true });

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <CodeMirror
        value={value}
        height="200px"
        theme={theme === "dark" ? "dark" : "light"}
        extensions={[extension]}
        onChange={onChange}
        editable={!disabled}
        basicSetup={{ lineNumbers: true, foldGutter: false }}
      />
    </div>
  );
}
