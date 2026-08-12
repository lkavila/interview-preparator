import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import AiExtraExercise from "../components/AiExtraExercise";
import { pick } from "../lib/lang";
import { useCourseQuery } from "../store/api";

export default function CoursePage() {
  const { slug } = useParams<{ slug: string }>();
  const { t, i18n } = useTranslation();
  const { data: course, isLoading, isError } = useCourseQuery(slug!);

  if (isLoading) return <p className="text-muted">...</p>;
  if (isError || !course) return <p className="text-error">{t("loadFailed")}</p>;

  const pct =
    course.lesson_count > 0
      ? Math.round((course.completed_lessons / course.lesson_count) * 100)
      : 0;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <Link to="/" className="text-[13px] text-muted hover:text-text">
          ← {t("courses")}
        </Link>
        <h1 className="mt-2 text-xl font-semibold">{pick(course.title, i18n.language)}</h1>
        <p className="mt-1 text-[14px] text-muted">{pick(course.description, i18n.language)}</p>
        <div className="mt-4 flex items-center gap-4">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface2">
            <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-[13px] text-muted">
            {course.completed_lessons}/{course.lesson_count} {t("completed")}
          </span>
        </div>
      </div>

      <ol className="space-y-2">
        {course.lessons.map((lesson, i) => (
          <li key={lesson.id}>
            <Link
              to={`/lessons/${lesson.id}`}
              className="card flex items-center gap-4 px-4 py-3 transition-colors hover:border-accent"
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[12px] font-medium ${
                  lesson.completed
                    ? "bg-success-soft text-success"
                    : "bg-surface2 text-muted"
                }`}
              >
                {lesson.completed ? (
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  i + 1
                )}
              </span>
              <span className="text-[14px]">{pick(lesson.question, i18n.language)}</span>
            </Link>
          </li>
        ))}
      </ol>

      {course.test_question_count > 0 && (
        <div className="card mt-6 flex items-center justify-between p-5">
          <div>
            <h2 className="text-[15px] font-semibold">{t("finalTest")}</h2>
            <p className="text-[13px] text-muted">
              {course.test_question_count} {i18n.language === "es" ? "preguntas" : "questions"}
              {course.best_test_score != null &&
                ` · ${t("bestScore")}: ${Math.round(course.best_test_score)}%`}
            </p>
          </div>
          <Link to={`/courses/${course.slug}/test`} className="btn btn-primary">
            {course.best_test_score != null ? t("retakeTest") : t("start")}
          </Link>
        </div>
      )}

      <AiExtraExercise courseSlug={course.slug} />
    </div>
  );
}
