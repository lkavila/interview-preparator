import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { onBadgesEarned } from "../../lib/badgeEvents";
import { pick } from "../../lib/lang";
import { useBadgesQuery } from "../../store/api";

interface Toast {
  id: number;
  key: string;
}

let toastId = 0;

/** Global toast shown whenever the backend reports a newly earned badge. */
export default function BadgeToaster() {
  const { t, i18n } = useTranslation();
  const [toasts, setToasts] = useState<Toast[]>([]);
  const { data: badges } = useBadgesQuery();

  useEffect(() => {
    return onBadgesEarned((keys) => {
      const next = keys.map((key) => ({ id: ++toastId, key }));
      setToasts((prev) => [...prev, ...next]);
      next.forEach((toast) =>
        setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== toast.id)), 5000)
      );
    });
  }, []);

  return (
    <div
      className="pointer-events-none fixed bottom-5 right-5 z-50 flex flex-col gap-2"
      aria-live="polite"
    >
      <AnimatePresence>
        {toasts.map((toast) => {
          const badge = badges?.find((b) => b.key === toast.key);
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 60, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 60 }}
              className="card pointer-events-auto flex items-center gap-3 border-accent/50 px-4 py-3 shadow-lg"
            >
              <motion.span
                className="text-2xl"
                animate={{ rotate: [0, -12, 12, 0] }}
                transition={{ duration: 0.6, delay: 0.15 }}
                aria-hidden="true"
              >
                {badge?.icon ?? "🏅"}
              </motion.span>
              <div>
                <p className="text-[12px] font-medium uppercase tracking-wide text-accent">
                  {t("badgeEarned")}
                </p>
                <p className="text-[13.5px] font-semibold">
                  {badge ? pick(badge.name, i18n.language) : toast.key}
                </p>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
