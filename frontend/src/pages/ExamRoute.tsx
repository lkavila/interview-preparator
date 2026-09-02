import { useParams } from "react-router-dom";
import SequentialExamPage from "./SequentialExamPage";
import TestPage from "./TestPage";
import { useCourseQuery } from "../store/api";

/** Picks the exam UI that matches the exam's shape.
 *
 * Question-bank exams are drawn fresh and strictly timed, so they run one
 * question at a time; fixed exams keep the scrollable list. The course query is
 * already cached, so the chosen page re-reads it for free. */
export default function ExamRoute() {
  const { slug, examSlug } = useParams<{ slug: string; examSlug: string }>();
  const { data: course, isLoading } = useCourseQuery(slug!);

  if (isLoading) return <p className="text-muted">...</p>;
  const exam = course?.exams.find((e) => e.slug === examSlug);
  return exam?.sampling ? <SequentialExamPage /> : <TestPage />;
}
