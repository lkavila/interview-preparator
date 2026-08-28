import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import AnalyticsPage from "./pages/AnalyticsPage";
import CoursePage from "./pages/CoursePage";
import DashboardPage from "./pages/DashboardPage";
import LessonPage from "./pages/LessonPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import SettingsPage from "./pages/SettingsPage";
import TestPage from "./pages/TestPage";
import type { RootState } from "./store";

export default function App() {
  const { token, user } = useSelector((s: RootState) => s.auth);
  const { i18n } = useTranslation();

  useEffect(() => {
    const theme = user?.theme ?? "dark";
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [user?.theme]);

  useEffect(() => {
    const lang = user?.language ?? i18n.language ?? "es";
    if (i18n.language !== lang) i18n.changeLanguage(lang);
  }, [user?.language, i18n]);

  if (!token) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/courses/:slug" element={<CoursePage />} />
        <Route path="/courses/:slug/test" element={<TestPage />} />
        <Route path="/courses/:slug/exams/:examSlug" element={<TestPage />} />
        <Route path="/lessons/:id" element={<LessonPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
