import { useState } from "react";
import { useTranslation } from "react-i18next";
import { renderMarkdown } from "../lib/lang";
import { useTutorMutation } from "../store/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function AiTutor({ lessonId }: { lessonId?: number }) {
  const { t } = useTranslation();
  const [tutor, { isLoading }] = useTutorMutation();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState(false);

  const send = async () => {
    const question = input.trim();
    if (!question || isLoading) return;
    setError(false);
    setInput("");
    setMessages((m) => [...m, { role: "user", content: question }]);
    try {
      const res = await tutor({ question, lesson_id: lessonId }).unwrap();
      setMessages((m) => [...m, { role: "assistant", content: res.answer }]);
    } catch {
      setError(true);
    }
  };

  return (
    <div className="card p-5">
      <h3 className="mb-3 flex items-center gap-2 text-base font-semibold">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
          <path d="M12 8V4H8" />
          <rect x="4" y="8" width="16" height="12" rx="2" />
          <path d="M2 14h2m16 0h2M9 13v2m6-2v2" />
        </svg>
        {t("aiTutor")}
      </h3>
      <div className="space-y-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`rounded-lg px-3.5 py-2.5 text-sm ${
              m.role === "user" ? "bg-accent-soft" : "bg-surface2"
            }`}
          >
            {m.role === "assistant" ? (
              <div
                className="prose-content"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(m.content) }}
              />
            ) : (
              m.content
            )}
          </div>
        ))}
        {isLoading && <p className="text-sm text-muted">{t("aiThinking")}</p>}
        {error && <p className="text-sm text-warning">{t("aiUnavailable")}</p>}
      </div>
      <div className="mt-3 flex gap-2">
        <input
          className="input"
          placeholder={t("askTutor")}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="btn" onClick={send} disabled={isLoading || !input.trim()}>
          {t("send")}
        </button>
      </div>
    </div>
  );
}
