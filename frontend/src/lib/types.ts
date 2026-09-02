export type Bilingual = { en: string; es: string };

export interface User {
  id: number;
  email: string;
  name: string;
  language: "en" | "es";
  theme: "dark" | "light";
}

export interface TokenResponse {
  access_token: string;
  user: User;
}

export interface CourseSummary {
  id: number;
  slug: string;
  order_index: number;
  icon: string;
  title: Bilingual;
  description: Bilingual;
  lesson_count: number;
  completed_lessons: number;
  best_test_score: number | null;
}

export interface LessonSummary {
  id: number;
  slug: string;
  order_index: number;
  question: Bilingual;
  completed: boolean;
}

export interface CourseExam {
  slug: string;
  order_index: number;
  title: Bilingual;
  description: Bilingual;
  /** For a sampled exam this is the size of the draw, not of the bank. */
  question_count: number;
  pass_score: number;
  time_limit_minutes: number | null;
  best_score: number | null;
  attempts: number;
  /** Per-category quotas; non-null only on question-bank exams. */
  sampling: Record<string, number> | null;
  bank_size: number | null;
}

export interface CourseDetail extends CourseSummary {
  lessons: LessonSummary[];
  test_question_count: number;
  exams: CourseExam[];
}

export type ExerciseType =
  | "multiple_choice"
  | "matching"
  | "ordering"
  | "table_builder"
  | "sql"
  | "code"
  | "open_text";

export interface ExerciseData {
  prompt: Bilingual;
  options?: Bilingual[];
  multiple?: boolean;
  left?: { id: string; label: Bilingual }[];
  right?: { id: string; label: Bilingual }[];
  items?: { id: string; label: Bilingual }[];
  layout?: "flow" | "list";
  type_options?: string[];
  column_count?: number;
  setup_sql?: string;
  verification_query?: string;
  hint?: Bilingual;
  language?: "javascript" | "typescript" | "python" | "sql" | "go";
  starter_code?: string;
  explanation?: Bilingual;
  /** Inline figure for lesson exercises (exam questions use the column). */
  svg_content?: string;
}

export interface Exercise {
  id: number;
  order_index: number;
  type: ExerciseType;
  validation_mode: "static" | "llm";
  data: ExerciseData;
}

export interface LessonContent {
  question: Bilingual;
  definition: Bilingual;
  examples: Bilingual[];
}

export type LessonComponentType =
  | "quiz_card"
  | "interview_question_card"
  | "fun_fact_carousel"
  | "concept_diagram"
  | "image_gallery"
  | "sql_playground";

export interface GalleryImage {
  src: string;
  title: string;
  author: string;
  license: string;
  source_url: string;
}

export interface PlaygroundSample {
  label: Bilingual;
  sql: string;
}

export interface LessonComponentConfig {
  /** image_gallery / fun_fact_carousel */
  images?: GalleryImage[];
  /** concept_diagram */
  kind?: "mermaid" | "chart";
  code?: string;
  caption?: Bilingual;
  chart?: { type: "bar" | "line"; data: { name: string; value: number }[]; label?: Bilingual };
  /** sql_playground */
  schema_sql?: string;
  title?: Bilingual;
  intro?: Bilingual;
  initial_query?: string;
  samples?: PlaygroundSample[];
  max_rows?: number;
}

export interface LessonComponent {
  id: number;
  component_type: LessonComponentType;
  order_index: number;
  config: LessonComponentConfig;
}

export interface Lesson {
  id: number;
  slug: string;
  order_index: number;
  course_slug: string;
  course_title: Bilingual;
  content: LessonContent;
  exercises: Exercise[];
  components: LessonComponent[];
  completed: boolean;
  prev_lesson_id: number | null;
  next_lesson_id: number | null;
}

export interface EnrichmentInterviewQuestion {
  question: string;
  suggested_answer: string;
}

export interface EnrichmentQuizItem {
  question: string;
  options: string[];
  correct_index: number;
}

export interface Enrichment {
  source: "llm" | "fallback";
  fun_facts: string[];
  interview_questions: EnrichmentInterviewQuestion[];
  quiz: EnrichmentQuizItem[];
}

export interface Badge {
  key: string;
  icon: string;
  name: Bilingual;
  description: Bilingual;
  earned: boolean;
  earned_at: string | null;
}

export interface AttemptResponse {
  correct: boolean;
  feedback: string | null;
  solution: Record<string, unknown> | null;
  new_badges: string[];
}

export interface SolutionReveal {
  answer: string;
  source: "llm" | "reference";
}

export type QuestionCategory = "VERBAL" | "NUMERIC" | "LOGIC";

export interface TestQuestion {
  id: number;
  order_index: number;
  type: "multiple_choice" | "open_text";
  /** Set on question-bank exams so results can be broken down by topic. */
  category: QuestionCategory | null;
  data: ExerciseData;
  svg_content: string | null;
}

export interface TestQuestionResult {
  question_id: number;
  correct: boolean;
  feedback: string | null;
  solution: Record<string, unknown> | null;
}

export interface TestResult {
  score: number;
  correct: number;
  total: number;
  pass_score: number;
  results: TestQuestionResult[];
  new_badges: string[];
  /** Submitted past the server deadline: graded, but it does not count. */
  timed_out: boolean;
}

/** A started timed attempt, as returned by /start and /sessions/{token}. */
export interface ExamSessionResponse {
  session_token: string;
  /** ISO timestamps. The client syncs its countdown to these, not to its own clock. */
  server_time: string;
  expires_at: string;
  seconds_remaining: number;
  time_limit_minutes: number | null;
  pass_score: number;
  questions: TestQuestion[];
}

export interface ExamSessionState {
  token: string;
  questions: TestQuestion[];
  /** Epoch ms of the deadline, already corrected for client clock skew. */
  deadline: number;
  passScore: number;
  timeLimitMinutes: number | null;
}

export interface StudyDay {
  day: string;
  seconds: number;
  new_badges?: string[];
}

export interface CourseAccuracy {
  course_slug: string;
  course_title: Bilingual;
  attempts: number;
  correct: number;
  accuracy: number;
}

export interface LessonAccuracy {
  lesson_id: number;
  lesson_slug: string;
  question: Bilingual;
  course_slug: string;
  attempts: number;
  correct: number;
  accuracy: number;
}

export interface AnalyticsSummary {
  total_attempts: number;
  total_correct: number;
  overall_accuracy: number;
  total_study_seconds: number;
  study_days: StudyDay[];
  by_course: CourseAccuracy[];
  weakest_lessons: LessonAccuracy[];
  strongest_lessons: LessonAccuracy[];
}

export interface GeneratedExercise {
  prompt: Bilingual;
  options: Bilingual[];
  correct: number;
  explanation: Bilingual;
}
