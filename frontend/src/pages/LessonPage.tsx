import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import AiTutor from "../components/AiTutor";
import ExerciseCard from "../components/exercises/ExerciseCard";
import LessonComponents from "../components/lesson/LessonComponents";
import { pick, renderMarkdown } from "../lib/lang";
import { useCompleteLessonMutation, useLessonQuery } from "../store/api";

export default function LessonPage() {
  const { id } = useParams<{ id: string }>();
  const lessonId = Number(id);
  const { t, i18n } = useTranslation();
  const { data: lesson, isLoading, isError } = useLessonQuery(lessonId);
  const [completeLesson, { isLoading: completing }] = useCompleteLessonMutation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [lessonId]);

  if (isLoading) return <p className="text-muted">...</p>;
  if (isError || !lesson) return <p className="text-error">{t("loadFailed")}</p>;

  const lang = i18n.language;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5">
        <Link to={`/courses/${lesson.course_slug}`} className="text-sm text-muted hover:text-text">
          ← {pick(lesson.course_title, lang)}
        </Link>
        <p className="mt-3 text-xs font-medium uppercase tracking-wider text-accent">
          {t("question")}
        </p>
        <h1 className="mt-1 text-xl font-semibold leading-snug">
          {pick(lesson.content.question, lang)}
        </h1>
      </div>

      <section className="card mb-4 p-4 sm:p-5">
        <h2 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">
          {t("definition")}
        </h2>
        <div
          className="prose-content text-base"
          dangerouslySetInnerHTML={{
            __html: renderMarkdown(pick(lesson.content.definition, lang)),
          }}
        />
      </section>

      <section className="card mb-4 p-4 sm:p-5">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted">
          {t("examples")}
        </h2>
        <ul className="space-y-3">
          {lesson.content.examples.map((ex, i) => (
            <li key={i} className="flex gap-3 text-base">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <div
                className="prose-content"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(pick(ex, lang)) }}
              />
            </li>
          ))}
        </ul>
      </section>

      <div className="mb-4">
        <LessonComponents lessonId={lesson.id} components={lesson.components} />
      </div>

      <h2 className="mb-3 mt-6 text-xs font-medium uppercase tracking-wider text-muted">
        {t("exercises")}
      </h2>
      <div className="space-y-4">
        {lesson.exercises.map((exercise, i) => (
          <ExerciseCard key={exercise.id} exercise={exercise} index={i} />
        ))}
      </div>

      <div className="mt-6">
        <AiTutor lessonId={lesson.id} />
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <div>
          {lesson.prev_lesson_id && (
            <Link to={`/lessons/${lesson.prev_lesson_id}`} className="btn w-full sm:w-auto">
              ← {t("prevLesson")}
            </Link>
          )}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          {lesson.completed ? (
            <span className="rounded-md bg-success-soft px-3 py-1.5 text-sm font-medium text-success">
              {t("lessonCompleted")}
            </span>
          ) : (
            <button
              className="btn btn-primary w-full sm:w-auto"
              disabled={completing}
              onClick={() =>
                completeLesson({ lessonId: lesson.id, courseSlug: lesson.course_slug })
              }
            >
              {t("markComplete")}
            </button>
          )}
          {lesson.next_lesson_id && (
            <Link to={`/lessons/${lesson.next_lesson_id}`} className="btn w-full sm:w-auto">
              {t("nextLesson")} →
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
