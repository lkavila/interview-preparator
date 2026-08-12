import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useDispatch } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { useLoginMutation } from "../store/api";
import { setCredentials } from "../store/authSlice";

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [login, { isLoading }] = useLoginMutation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const res = await login({ email, password }).unwrap();
      dispatch(setCredentials({ token: res.access_token, user: res.user }));
      navigate("/");
    } catch {
      setError(t("invalidCredentials"));
    }
  };

  return (
    <div className="flex min-h-full items-center justify-center px-4">
      <div className="card w-full max-w-sm p-8">
        <div className="mb-6 text-center">
          <h1 className="text-lg font-semibold">{t("appName")}</h1>
          <p className="mt-1 text-[13px] text-muted">{t("tagline")}</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="mb-1 block text-[13px] font-medium text-muted">{t("email")}</label>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-[13px] font-medium text-muted">{t("password")}</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <p className="text-[13px] text-error">{error}</p>}
          <button className="btn btn-primary w-full justify-center" disabled={isLoading}>
            {t("login")}
          </button>
        </form>
        <p className="mt-5 text-center text-[13px] text-muted">
          {t("noAccount")}{" "}
          <Link to="/register" className="text-accent hover:underline">
            {t("register")}
          </Link>
        </p>
        <div className="mt-4 flex justify-center gap-2">
          <button
            className={`text-[12px] ${i18n.language === "en" ? "text-accent" : "text-muted"}`}
            onClick={() => i18n.changeLanguage("en")}
          >
            English
          </button>
          <span className="text-muted">·</span>
          <button
            className={`text-[12px] ${i18n.language === "es" ? "text-accent" : "text-muted"}`}
            onClick={() => i18n.changeLanguage("es")}
          >
            Español
          </button>
        </div>
      </div>
    </div>
  );
}
