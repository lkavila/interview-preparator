import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";
import { pick } from "../lib/lang";
import type { RootState } from "../store";
import { useCoursesQuery } from "../store/api";

const ICONS: Record<string, string> = {
  cpu: "M9 2v2m6-2v2M9 20v2m6-2v2M2 9h2m-2 6h2M20 9h2m-2 6h2M6 6h12v12H6zM9 9h6v6H9z",
  server: "M2 5h20v6H2zM2 13h20v6H2zM6 8h.01M6 16h.01",
  network: "M12 2v6m0 8v6M2 12h6m8 0h6M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z",
  zap: "M13 2 3 14h9l-1 8 10-12h-9l1-8z",
  database: "M12 2C7.6 2 4 3.3 4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5c0-1.7-3.6-3-8-3zM4 5c0 1.7 3.6 3 8 3s8-1.3 8-3M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  bolt: "M13 2 3 14h9l-1 8 10-12h-9l1-8z",
  queue: "M3 6h18M3 12h18M3 18h12",
  kubernetes: "M12 2 3 7v10l9 5 9-5V7l-9-5zM12 8v8m-4-6 8 4m0-4-8 4",
  cloud: "M17.5 19a4.5 4.5 0 1 0-.42-8.98A6 6 0 1 0 6 16.5",
  python: "M12 2c-2 0-4 .5-4 2.5V7h8v1H6a4 4 0 0 0-4 4c0 2.2 1 4 3 4h1v-2.5A3.5 3.5 0 0 1 9.5 10h5A2.5 2.5 0 0 0 17 7.5v-3C17 2.5 14 2 12 2zM12 22c2 0 4-.5 4-2.5V17H8v-1h10a4 4 0 0 0 4-4c0-2.2-1-4-3-4h-1v2.5a3.5 3.5 0 0 1-3.5 3.5h-5A2.5 2.5 0 0 0 7 16.5v3c0 2 3 2.5 5 2.5z",
  globe: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM2 12h20M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z",
  eye: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  book: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
};

export default function DashboardPage() {
  const { t, i18n } = useTranslation();
  const user = useSelector((s: RootState) => s.auth.user);
  const { data: courses, isLoading, isError } = useCoursesQuery();

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">
          {t("welcomeBack")}, {user?.name}
        </h1>
        <p className="text-[13.5px] text-muted">{t("keepGoing")}</p>
      </div>

      {isLoading && <p className="text-muted">...</p>}
      {isError && <p className="text-error">{t("loadFailed")}</p>}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {courses?.map((course) => {
          const pct =
            course.lesson_count > 0
              ? Math.round((course.completed_lessons / course.lesson_count) * 100)
              : 0;
          return (
            <Link
              key={course.id}
              to={`/courses/${course.slug}`}
              className="card group flex flex-col p-5 transition-colors hover:border-accent"
            >
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d={ICONS[course.icon] ?? ICONS.book} />
                  </svg>
                </span>
                <h2 className="text-[14.5px] font-semibold leading-tight">
                  {pick(course.title, i18n.language)}
                </h2>
              </div>
              <p className="mb-4 line-clamp-2 text-[13px] text-muted">
                {pick(course.description, i18n.language)}
              </p>
              <div className="mt-auto">
                <div className="mb-1.5 flex items-center justify-between text-[12px] text-muted">
                  <span>
                    {course.completed_lessons}/{course.lesson_count} {t("lessons")}
                  </span>
                  <span className="flex items-center gap-2">
                    {course.best_test_score != null && (
                      <span className="text-accent">
                        {t("bestScore")}: {Math.round(course.best_test_score)}%
                      </span>
                    )}
                    {pct}%
                  </span>
                </div>
                <div className="h-1 overflow-hidden rounded-full bg-surface2">
                  <div
                    className="h-full rounded-full bg-accent transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
