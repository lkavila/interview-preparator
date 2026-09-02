import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatClock } from "../../lib/lang";

interface Props {
  /** Epoch ms, already corrected for clock skew against the server. */
  deadline: number;
  /** Fired exactly once when the clock reaches zero. */
  onExpire: () => void;
  /** Seconds left at which the timer turns red. */
  warnAt?: number;
}

/** Counts down to a deadline owned by the server.
 *
 * The deadline arrives from /start already offset by the difference between the
 * server clock and this browser's, so a skewed local clock cannot buy time. */
export default function ExamCountdown({ deadline, onExpire, warnAt = 60 }: Props) {
  const { t } = useTranslation();
  const [secondsLeft, setSecondsLeft] = useState(() =>
    Math.max(0, Math.round((deadline - Date.now()) / 1000))
  );

  // The interval and a manual submit can race; only the first one wins.
  const firedRef = useRef(false);
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  useEffect(() => {
    firedRef.current = false;
    const tick = () => {
      const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      setSecondsLeft(left);
      if (left <= 0 && !firedRef.current) {
        firedRef.current = true;
        window.clearInterval(id);
        onExpireRef.current();
      }
    };
    const id = window.setInterval(tick, 1000);
    tick();
    return () => window.clearInterval(id);
  }, [deadline]);

  const warning = secondsLeft <= warnAt;
  return (
    <div
      className={`sticky top-2 z-10 mb-4 flex items-center justify-between rounded-lg border px-4 py-2 text-sm ${
        warning ? "border-error bg-error-soft text-error" : "border-border bg-surface2 text-muted"
      }`}
      role="timer"
      aria-live={warning ? "assertive" : "off"}
    >
      <span>{t("timeLeft")}</span>
      <span className="font-mono text-base tabular-nums">{formatClock(secondsLeft)}</span>
    </div>
  );
}
