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
        <Link to="/" className="text-sm text-muted hover:text-text">
          ← {t("courses")}
        </Link>
        <h1 className="mt-2 text-xl font-semibold">{pick(course.title, i18n.language)}</h1>
        <p className="mt-1 text-base text-muted">{pick(course.description, i18n.language)}</p>
        <div className="mt-4 flex items-center gap-4">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface2">
            <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
          </div>
          <span className="text-sm text-muted">
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
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium ${
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
              <span className="text-base">{pick(lesson.question, i18n.language)}</span>
            </Link>
          </li>
        ))}
      </ol>

      {course.test_question_count > 0 && (
        <div className="card mt-6 flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5">
          <div>
            <h2 className="text-lg font-semibold">{t("finalTest")}</h2>
            <p className="text-sm text-muted">
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

      {course.exams.length > 0 && (
        <section className="mt-8">
          <h2 className="text-lg font-semibold">{t("practiceExams")}</h2>
          <p className="mb-3 text-sm text-muted">{t("practiceExamsHint")}</p>
          <ul className="space-y-2">
            {course.exams.map((exam) => (
              <li key={exam.slug}>
                <Link
                  to={`/courses/${course.slug}/exams/${exam.slug}`}
                  className="card flex flex-col gap-3 p-4 transition-colors hover:border-accent sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="text-base font-medium">{pick(exam.title, i18n.language)}</p>
                    <p className="mt-0.5 text-sm text-muted">
                      {exam.question_count} {t("questionsLabel")}
                      {exam.time_limit_minutes != null &&
                        ` · ${exam.time_limit_minutes} ${t("minutes")}`}
                      {` · ${t("passMark")}: ${Math.round(exam.pass_score)}%`}
                    </p>
                    {pick(exam.description, i18n.language) && (
                      <p className="mt-1 text-sm text-muted">
                        {pick(exam.description, i18n.language)}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    {exam.best_score != null && (
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                          exam.best_score >= exam.pass_score
                            ? "bg-success-soft text-success"
                            : "bg-error-soft text-error"
                        }`}
                      >
                        {t("bestScore")}: {Math.round(exam.best_score)}%
                      </span>
                    )}
                    <span className="btn btn-primary">
                      {exam.attempts > 0 ? t("retakeExam") : t("startExam")}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <AiExtraExercise courseSlug={course.slug} />
    </div>
  );
}
