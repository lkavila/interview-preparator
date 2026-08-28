import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatDuration } from "../lib/lang";
import { useHeartbeatMutation, useStudyTodayQuery } from "../store/api";

const HEARTBEAT_SECONDS = 60;
const IDLE_LIMIT_MS = 120_000; // pause after 2 min without interaction

/** Always-visible daily study timer. Counts seconds while the tab is visible
 * and the user is active; flushes to the backend every 60s. */
export default function StudyTimer() {
  const { t } = useTranslation();
  const { data: today } = useStudyTodayQuery();
  const [heartbeat] = useHeartbeatMutation();

  const [localSeconds, setLocalSeconds] = useState(0);
  const baseSeconds = today?.seconds ?? 0;
  const pendingRef = useRef(0);
  const lastActivityRef = useRef(Date.now());
  const [active, setActive] = useState(true);

  useEffect(() => {
    const markActivity = () => {
      lastActivityRef.current = Date.now();
    };
    const events = ["mousemove", "keydown", "click", "scroll", "touchstart"] as const;
    events.forEach((e) => window.addEventListener(e, markActivity, { passive: true }));
    return () => events.forEach((e) => window.removeEventListener(e, markActivity));
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      const visible = document.visibilityState === "visible";
      const fresh = Date.now() - lastActivityRef.current < IDLE_LIMIT_MS;
      const isActive = visible && fresh;
      setActive(isActive);
      if (!isActive) return;

      setLocalSeconds((s) => s + 1);
      pendingRef.current += 1;
      if (pendingRef.current >= HEARTBEAT_SECONDS) {
        const seconds = pendingRef.current;
        pendingRef.current = 0;
        heartbeat({ seconds }).catch(() => {
          pendingRef.current += seconds; // retry on next flush
        });
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [heartbeat]);

  // Flush remaining seconds when leaving the page
  useEffect(() => {
    const flush = () => {
      if (pendingRef.current > 0) {
        const auth = localStorage.getItem("auth");
        const token = auth ? JSON.parse(auth).token : null;
        if (token) {
          const blob = new Blob([JSON.stringify({ seconds: pendingRef.current })], {
            type: "application/json",
          });
          // sendBeacon can't set headers, so fall back to fetch keepalive
          fetch("/api/study/heartbeat", {
            method: "POST",
            keepalive: true,
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
            body: blob,
          }).catch(() => undefined);
        }
        pendingRef.current = 0;
      }
    };
    window.addEventListener("beforeunload", flush);
    return () => {
      window.removeEventListener("beforeunload", flush);
      flush();
    };
  }, []);

  const total = baseSeconds + localSeconds;

  return (
    <div
      className="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-muted"
      title={t("studyTime")}
    >
      <span
        className={`inline-block h-2 w-2 rounded-full ${active ? "bg-success" : "bg-border"}`}
      />
      <span className="font-mono tabular-nums text-text">{formatDuration(total)}</span>
      <span className="hidden sm:inline">{t("studyToday").toLowerCase()}</span>
    </div>
  );
}
