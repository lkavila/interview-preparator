import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useDispatch, useSelector } from "react-redux";
import type { RootState } from "../store";
import { useUpdatePreferencesMutation } from "../store/api";
import { setUser } from "../store/authSlice";

export default function SettingsPage() {
  const { t } = useTranslation();
  const dispatch = useDispatch();
  const user = useSelector((s: RootState) => s.auth.user);
  const [updatePrefs, { isLoading }] = useUpdatePreferencesMutation();
  const [name, setName] = useState(user?.name ?? "");
  const [saved, setSaved] = useState(false);

  if (!user) return null;

  const apply = async (patch: { language?: "en" | "es"; theme?: "dark" | "light"; name?: string }) => {
    dispatch(setUser({ ...user, ...patch }));
    setSaved(false);
    try {
      const updated = await updatePrefs(patch).unwrap();
      dispatch(setUser(updated as typeof user));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      /* local change kept */
    }
  };

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-6 text-xl font-semibold">{t("settings")}</h1>

      <div className="card space-y-6 p-6">
        <div>
          <label className="mb-1 block text-sm font-medium text-muted">{t("name")}</label>
          <div className="flex gap-2">
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
            <button
              className="btn"
              disabled={isLoading || !name.trim() || name === user.name}
              onClick={() => apply({ name })}
            >
              {t("save")}
            </button>
          </div>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-muted">{t("language")}</p>
          <div className="flex gap-2">
            {(["en", "es"] as const).map((lang) => (
              <button
                key={lang}
                className={`btn ${user.language === lang ? "border-accent text-accent" : ""}`}
                onClick={() => apply({ language: lang })}
              >
                {lang === "en" ? t("english") : t("spanish")}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-muted">{t("theme")}</p>
          <div className="flex gap-2">
            {(["dark", "light"] as const).map((theme) => (
              <button
                key={theme}
                className={`btn ${user.theme === theme ? "border-accent text-accent" : ""}`}
                onClick={() => apply({ theme })}
              >
                {theme === "dark" ? t("dark") : t("light")}
              </button>
            ))}
          </div>
        </div>

        {saved && <p className="text-sm text-success">{t("saved")}</p>}
      </div>
    </div>
  );
}
