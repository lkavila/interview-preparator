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
    `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
      isActive ? "bg-accent-soft text-accent" : "text-muted hover:text-text"
    }`;

  // Bottom tab bar (mobile only). Same three destinations as the header nav.
  const tabClass = ({ isActive }: { isActive: boolean }) =>
    `flex flex-1 flex-col items-center justify-center gap-0.5 text-2xs font-medium transition-colors ${
      isActive ? "text-accent" : "text-muted"
    }`;

  const TABS = [
    {
      to: "/",
      end: true,
      label: t("courses"),
      path: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z",
    },
    {
      to: "/analytics",
      end: false,
      label: t("analytics"),
      path: "M3 3v18h18M7 15v3M12 9v9M17 12v6",
    },
    {
      to: "/settings",
      end: false,
      label: t("settings"),
      path: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9v.09a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z",
    },
  ];

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-border bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2 sm:gap-4 sm:py-2.5">
          <Link to="/" className="flex items-center gap-2 text-lg font-semibold text-text">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 text-accent">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <span className="hidden sm:inline">{t("appName")}</span>
          </Link>
          <nav className="hidden items-center gap-1 sm:flex">
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
          <div className="ml-auto flex items-center gap-1.5 sm:gap-2">
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
      <main className="app-main mx-auto max-w-6xl px-4 py-6">{children}</main>
      <nav
        className="bottom-nav fixed inset-x-0 bottom-0 z-30 flex border-t border-border bg-surface/95 backdrop-blur sm:hidden"
        style={{ height: "calc(var(--bottom-nav-h) + env(safe-area-inset-bottom, 0px))" }}
      >
        {TABS.map((tab) => (
          // NavLink already sets aria-current="page" on the anchor when active.
          <NavLink key={tab.to} to={tab.to} end={tab.end} className={tabClass}>
            <svg
              width="19"
              height="19"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden
            >
              <path d={tab.path} />
            </svg>
            <span>{tab.label}</span>
          </NavLink>
        ))}
      </nav>
      <BadgeToaster />
    </div>
  );
}
