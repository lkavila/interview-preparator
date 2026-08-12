import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import ProgressBadgeSystem from "../components/lesson/ProgressBadgeSystem";
import { formatDuration, pick } from "../lib/lang";
import { useAnalyticsQuery } from "../store/api";

export default function AnalyticsPage() {
  const { t, i18n } = useTranslation();
  const { data, isLoading, isError } = useAnalyticsQuery();

  if (isLoading) return <p className="text-muted">...</p>;
  if (isError || !data) return <p className="text-error">{t("loadFailed")}</p>;

  const lang = i18n.language;
  const hasData = data.total_attempts > 0;

  const studyData = data.study_days.map((d) => ({
    day: d.day.slice(5), // MM-DD
    minutes: Math.round(d.seconds / 60),
  }));

  const courseData = data.by_course.map((c) => ({
    name: pick(c.course_title, lang),
    accuracy: c.accuracy,
    attempts: c.attempts,
  }));

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold">{t("analytics")}</h1>

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <div className="card p-5">
          <p className="text-[12.5px] text-muted">{t("overallAccuracy")}</p>
          <p className="mt-1 text-2xl font-semibold">{data.overall_accuracy}%</p>
        </div>
        <div className="card p-5">
          <p className="text-[12.5px] text-muted">{t("totalAttempts")}</p>
          <p className="mt-1 text-2xl font-semibold">{data.total_attempts}</p>
        </div>
        <div className="card p-5">
          <p className="text-[12.5px] text-muted">{t("totalStudy")}</p>
          <p className="mt-1 text-2xl font-semibold">{formatDuration(data.total_study_seconds)}</p>
        </div>
      </div>

      <div className="mb-6">
        <ProgressBadgeSystem />
      </div>

      {!hasData && <p className="card p-6 text-center text-[14px] text-muted">{t("noData")}</p>}

      {studyData.length > 0 && (
        <div className="card mb-6 p-5">
          <h2 className="mb-4 text-[14px] font-semibold">{t("dailyStudy")}</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={studyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} width={36} />
              <Tooltip
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 13,
                  color: "var(--text)",
                }}
                formatter={(v) => [`${Number(v)} ${t("minutes")}`, t("studyTime")]}
              />
              <Bar dataKey="minutes" fill="var(--accent)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {courseData.length > 0 && (
        <div className="card mb-6 p-5">
          <h2 className="mb-4 text-[14px] font-semibold">{t("byCourse")}</h2>
          <ResponsiveContainer width="100%" height={Math.max(200, courseData.length * 42)}>
            <BarChart data={courseData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
              <YAxis
                type="category"
                dataKey="name"
                width={190}
                tick={{ fontSize: 12, fill: "var(--text)" }}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 13,
                  color: "var(--text)",
                }}
                formatter={(v, _n, item) => [
                  `${Number(v)}% (${(item as { payload?: { attempts?: number } }).payload?.attempts ?? 0} ${t("attempts")})`,
                  t("accuracy"),
                ]}
              />
              <Bar dataKey="accuracy" fill="var(--accent)" radius={[0, 3, 3, 0]} barSize={16} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {(data.weakest_lessons.length > 0 || data.strongest_lessons.length > 0) && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="card p-5">
            <h2 className="mb-3 text-[14px] font-semibold text-error">{t("weakTopics")}</h2>
            <ul className="space-y-2">
              {data.weakest_lessons.map((l) => (
                <li key={l.lesson_id}>
                  <Link
                    to={`/lessons/${l.lesson_id}`}
                    className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-[13.5px] hover:bg-surface2"
                  >
                    <span className="line-clamp-1">{pick(l.question, lang)}</span>
                    <span className="shrink-0 rounded bg-error-soft px-2 py-0.5 text-[12px] font-medium text-error">
                      {l.accuracy}%
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div className="card p-5">
            <h2 className="mb-3 text-[14px] font-semibold text-success">{t("strongTopics")}</h2>
            <ul className="space-y-2">
              {data.strongest_lessons.map((l) => (
                <li key={l.lesson_id}>
                  <Link
                    to={`/lessons/${l.lesson_id}`}
                    className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-[13.5px] hover:bg-surface2"
                  >
                    <span className="line-clamp-1">{pick(l.question, lang)}</span>
                    <span className="shrink-0 rounded bg-success-soft px-2 py-0.5 text-[12px] font-medium text-success">
                      {l.accuracy}%
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
