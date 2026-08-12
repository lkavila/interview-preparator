import { useTranslation } from "react-i18next";
import type { Enrichment, LessonComponent } from "../../lib/types";
import { useEnrichmentQuery } from "../../store/api";
import ConceptDiagram from "./ConceptDiagram";
import FunFactCarousel from "./FunFactCarousel";
import ImageGallery from "./ImageGallery";
import InterviewQuestionCard from "./InterviewQuestionCard";
import QuizCard from "./QuizCard";
import { CardSkeleton } from "./Skeleton";

interface LessonComponentsProps {
  lessonId: number;
  components: LessonComponent[];
}

function needsEnrichment(components: LessonComponent[]): boolean {
  return components.some((c) =>
    ["quiz_card", "interview_question_card", "fun_fact_carousel"].includes(c.component_type)
  );
}

function renderComponent(
  component: LessonComponent,
  enrichment: Enrichment | undefined,
  enrichmentLoading: boolean
) {
  const type = component.component_type;

  if (type === "concept_diagram") return <ConceptDiagram config={component.config} />;
  if (type === "image_gallery") return <ImageGallery images={component.config.images ?? []} />;

  // enrichment-driven components
  if (enrichmentLoading) return <CardSkeleton lines={4} />;
  if (!enrichment) return null;

  switch (type) {
    case "quiz_card":
      return <QuizCard quiz={enrichment.quiz} source={enrichment.source} />;
    case "interview_question_card":
      return (
        <InterviewQuestionCard
          questions={enrichment.interview_questions}
          source={enrichment.source}
        />
      );
    case "fun_fact_carousel":
      return (
        <FunFactCarousel
          facts={enrichment.fun_facts}
          images={component.config.images}
          source={enrichment.source}
        />
      );
    default:
      return null;
  }
}

/** Renders the DB-configured interactive components of a lesson, fetching the
 * LLM enrichment once the lesson is opened. */
export default function LessonComponents({ lessonId, components }: LessonComponentsProps) {
  const { t } = useTranslation();
  const wantsEnrichment = needsEnrichment(components);
  const { data: enrichment, isLoading, isFetching } = useEnrichmentQuery(lessonId, {
    skip: !wantsEnrichment,
  });
  const enrichmentLoading = wantsEnrichment && (isLoading || isFetching);

  if (components.length === 0) return null;

  const ordered = [...components].sort((a, b) => a.order_index - b.order_index);

  return (
    <div className="space-y-4">
      {enrichmentLoading && (
        <p className="text-center text-[12.5px] text-muted" aria-live="polite">
          {t("enrichmentLoading")}
        </p>
      )}
      {ordered.map((component) => (
        <div key={component.id}>{renderComponent(component, enrichment, enrichmentLoading)}</div>
      ))}
    </div>
  );
}
