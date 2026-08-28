import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { emitBadgesEarned } from "../lib/badgeEvents";
import type {
  AnalyticsSummary,
  AttemptResponse,
  Badge,
  CourseDetail,
  CourseSummary,
  Enrichment,
  GeneratedExercise,
  Lesson,
  SolutionReveal,
  StudyDay,
  TestQuestion,
  TestResult,
  TokenResponse,
  User,
} from "../lib/types";
import type { RootState } from "./index";

async function emitBadgesFrom(queryFulfilled: Promise<{ data: unknown }>): Promise<void> {
  try {
    const { data } = await queryFulfilled;
    emitBadgesEarned((data as { new_badges?: string[] }).new_badges);
  } catch {
    // request failed; nothing to emit
  }
}

export const api = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({
    baseUrl: "/api",
    prepareHeaders: (headers, { getState }) => {
      const token = (getState() as RootState).auth.token;
      if (token) headers.set("Authorization", `Bearer ${token}`);
      return headers;
    },
  }),
  tagTypes: ["Courses", "Course", "Lesson", "Analytics", "Study", "Badges"],
  endpoints: (builder) => ({
    register: builder.mutation<
      TokenResponse,
      { email: string; password: string; name: string; language: string }
    >({
      query: (body) => ({ url: "/auth/register", method: "POST", body }),
    }),
    login: builder.mutation<TokenResponse, { email: string; password: string }>({
      query: (body) => ({ url: "/auth/login", method: "POST", body }),
    }),
    updatePreferences: builder.mutation<
      User,
      { language?: string; theme?: string; name?: string }
    >({
      query: (body) => ({ url: "/auth/me", method: "PATCH", body }),
    }),

    courses: builder.query<CourseSummary[], void>({
      query: () => "/courses",
      providesTags: ["Courses"],
    }),
    course: builder.query<CourseDetail, string>({
      query: (slug) => `/courses/${slug}`,
      providesTags: (_r, _e, slug) => [{ type: "Course", id: slug }],
    }),
    lesson: builder.query<Lesson, number>({
      query: (id) => `/lessons/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Lesson", id }],
    }),
    completeLesson: builder.mutation<
      { ok: boolean; new_badges: string[] },
      { lessonId: number; courseSlug: string }
    >({
      query: ({ lessonId }) => ({ url: `/lessons/${lessonId}/complete`, method: "POST" }),
      invalidatesTags: (_r, _e, { lessonId, courseSlug }) => [
        { type: "Lesson", id: lessonId },
        { type: "Course", id: courseSlug },
        "Courses",
        "Badges",
      ],
      onQueryStarted: (_arg, { queryFulfilled }) => emitBadgesFrom(queryFulfilled),
    }),
    submitAttempt: builder.mutation<
      AttemptResponse,
      { exerciseId: number; answer: Record<string, unknown> }
    >({
      query: ({ exerciseId, answer }) => ({
        url: `/exercises/${exerciseId}/attempt`,
        method: "POST",
        body: { answer },
      }),
      invalidatesTags: ["Analytics", "Badges"],
      onQueryStarted: (_arg, { queryFulfilled }) => emitBadgesFrom(queryFulfilled),
    }),
    revealSolution: builder.query<SolutionReveal, number>({
      query: (exerciseId) => `/exercises/${exerciseId}/solution`,
      // The model answer is stable per exercise+language; cache it for the session.
      keepUnusedDataFor: 3600,
    }),
    enrichment: builder.query<Enrichment, number>({
      query: (lessonId) => `/lessons/${lessonId}/enrichment`,
      // LLM generation can take a while the first time; cache aggressively after.
      keepUnusedDataFor: 3600,
    }),
    badges: builder.query<Badge[], void>({
      query: () => "/badges",
      providesTags: ["Badges"],
    }),

    test: builder.query<TestQuestion[], string>({
      query: (slug) => `/courses/${slug}/test`,
    }),
    exam: builder.query<TestQuestion[], { slug: string; examSlug: string }>({
      query: ({ slug, examSlug }) => `/courses/${slug}/exams/${examSlug}`,
    }),
    submitExam: builder.mutation<
      TestResult,
      { slug: string; examSlug: string; answers: Record<number, Record<string, unknown>> }
    >({
      query: ({ slug, examSlug, answers }) => ({
        url: `/courses/${slug}/exams/${examSlug}/attempt`,
        method: "POST",
        body: { answers },
      }),
      invalidatesTags: (_r, _e, { slug }) => [
        { type: "Course", id: slug },
        "Courses",
        "Analytics",
        "Badges",
      ],
      onQueryStarted: (_arg, { queryFulfilled }) => emitBadgesFrom(queryFulfilled),
    }),
    submitTest: builder.mutation<
      TestResult,
      { slug: string; answers: Record<number, Record<string, unknown>> }
    >({
      query: ({ slug, answers }) => ({
        url: `/courses/${slug}/test/attempt`,
        method: "POST",
        body: { answers },
      }),
      invalidatesTags: (_r, _e, { slug }) => [
        { type: "Course", id: slug },
        "Courses",
        "Analytics",
        "Badges",
      ],
      onQueryStarted: (_arg, { queryFulfilled }) => emitBadgesFrom(queryFulfilled),
    }),

    studyToday: builder.query<StudyDay, void>({
      query: () => "/study/today",
      providesTags: ["Study"],
    }),
    heartbeat: builder.mutation<StudyDay, { seconds: number }>({
      query: (body) => ({ url: "/study/heartbeat", method: "POST", body }),
      onQueryStarted: (_arg, { queryFulfilled }) => emitBadgesFrom(queryFulfilled),
    }),

    analytics: builder.query<AnalyticsSummary, void>({
      query: () => "/analytics/summary",
      providesTags: ["Analytics"],
    }),

    aiStatus: builder.query<{ available: boolean }, void>({
      query: () => "/ai/status",
    }),
    tutor: builder.mutation<{ answer: string }, { question: string; lesson_id?: number }>({
      query: (body) => ({ url: "/ai/tutor", method: "POST", body }),
    }),
    generateExercise: builder.mutation<GeneratedExercise, { course_slug: string; topic?: string }>({
      query: (body) => ({ url: "/ai/generate-exercise", method: "POST", body }),
    }),
  }),
});

export const {
  useRegisterMutation,
  useLoginMutation,
  useUpdatePreferencesMutation,
  useCoursesQuery,
  useCourseQuery,
  useLessonQuery,
  useEnrichmentQuery,
  useBadgesQuery,
  useCompleteLessonMutation,
  useSubmitAttemptMutation,
  useLazyRevealSolutionQuery,
  useTestQuery,
  useSubmitTestMutation,
  useExamQuery,
  useSubmitExamMutation,
  useStudyTodayQuery,
  useHeartbeatMutation,
  useAnalyticsQuery,
  useAiStatusQuery,
  useTutorMutation,
  useGenerateExerciseMutation,
} = api;
