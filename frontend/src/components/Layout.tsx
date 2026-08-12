import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { useDispatch, useSelector } from "react-redux";
import { Link, NavLink, useNavigate } from "react-router-dom";
import type { RootState } from "../store";
import { api, useUpdatePreferencesMutation } from "../store/api";
import { logout, setUser } from "../store/authSlice";
import BadgeToaster from "./lesson/BadgeToaster";
import StudyTimer from "./StudyTimer";

export default function Layout({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const user = useSelector((s: RootState) => s.auth.user);
  const [updatePrefs] = useUpdatePreferencesMutation();

  const toggleTheme = async () => {
    if (!user) return;
    const theme = user.theme === "dark" ? "light" : "dark";
    dispatch(setUser({ ...user, theme }));
    try {
      await updatePrefs({ theme }).unwrap();
    } catch {
      /* keep local preference */
    }
  };

  const toggleLanguage = async () => {
    if (!user) return;
    const language = user.language === "es" ? "en" : "es";
    dispatch(setUser({ ...user, language }));
    try {
      await updatePrefs({ language }).unwrap();
    } catch {
      /* keep local preference */
    }
  };

  const handleLogout = () => {
    dispatch(logout());
    dispatch(api.util.resetApiState());
    navigate("/login");
  };

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-[13.5px] font-medium transition-colors ${
      isActive ? "bg-accent-soft text-accent" : "text-muted hover:text-text"
    }`;

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-border bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-2.5">
          <Link to="/" className="flex items-center gap-2 text-[15px] font-semibold text-text">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span className="hidden sm:inline">{t("appName")}</span>
          </Link>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navClass}>
              {t("courses")}
            </NavLink>
            <NavLink to="/analytics" className={navClass}>
              {t("analytics")}
            </NavLink>
            <NavLink to="/settings" className={navClass}>
              {t("settings")}
            </NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <StudyTimer />
            <button
              onClick={toggleLanguage}
              className="btn !px-2.5"
              title={t("language")}
              aria-label={t("language")}
            >
              {user?.language === "es" ? "ES" : "EN"}
            </button>
            <button
              onClick={toggleTheme}
              className="btn !px-2.5"
              title={t("theme")}
              aria-label={t("theme")}
            >
              {user?.theme === "dark" ? (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4" />
                </svg>
              )}
            </button>
            <button onClick={handleLogout} className="btn !px-2.5" title={t("logout")}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
      <BadgeToaster />
    </div>
  );
}
