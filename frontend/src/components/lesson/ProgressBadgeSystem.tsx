import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { pick } from "../../lib/lang";
import { useBadgesQuery } from "../../store/api";
import { CardSkeleton } from "./Skeleton";

/** Achievements grid: earned badges in color, locked ones dimmed. */
export default function ProgressBadgeSystem() {
  const { t, i18n } = useTranslation();
  const { data: badges, isLoading } = useBadgesQuery();

  if (isLoading) return <CardSkeleton lines={4} title={t("badges")} />;
  if (!badges) return null;

  const earnedCount = badges.filter((b) => b.earned).length;

  return (
    <section className="card p-5" aria-label={t("badges")}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted">
          🏅 {t("badges")}
        </h2>
        <span className="text-sm text-muted">
          {earnedCount}/{badges.length}
        </span>
      </div>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {badges.map((badge, i) => (
          <motion.li
            key={badge.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.03 }}
            className={`rounded-lg border p-3 text-center ${
              badge.earned
                ? "border-accent/40 bg-accent-soft"
                : "border-border bg-surface2/40 opacity-60"
            }`}
            aria-label={`${pick(badge.name, i18n.language)}: ${
              badge.earned ? t("earned") : t("locked")
            }`}
          >
            <span className={`text-2xl ${badge.earned ? "" : "grayscale"}`} aria-hidden="true">
              {badge.icon}
            </span>
            <p className="mt-1 text-xs font-semibold leading-tight">
              {pick(badge.name, i18n.language)}
            </p>
            <p className="mt-0.5 text-2xs leading-snug text-muted">
              {pick(badge.description, i18n.language)}
            </p>
          </motion.li>
        ))}
      </ul>
    </section>
  );
}
