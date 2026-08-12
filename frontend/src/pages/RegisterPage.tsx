import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useDispatch } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { useRegisterMutation } from "../store/api";
import { setCredentials } from "../store/authSlice";

export default function RegisterPage() {
  const { t, i18n } = useTranslation();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [register, { isLoading }] = useRegisterMutation();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const res = await register({
        name,
        email,
        password,
        language: i18n.language === "es" ? "es" : "en",
      }).unwrap();
      dispatch(setCredentials({ token: res.access_token, user: res.user }));
      navigate("/");
    } catch (err: unknown) {
      const status = (err as { status?: number }).status;
      setError(status === 409 ? t("emailTaken") : t("invalidCredentials"));
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
            <label className="mb-1 block text-[13px] font-medium text-muted">{t("name")}</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-[13px] font-medium text-muted">{t("email")}</label>
            <input
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-[13px] font-medium text-muted">{t("password")}</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={6}
              required
            />
          </div>
          {error && <p className="text-[13px] text-error">{error}</p>}
          <button className="btn btn-primary w-full justify-center" disabled={isLoading}>
            {t("register")}
          </button>
        </form>
        <p className="mt-5 text-center text-[13px] text-muted">
          {t("haveAccount")}{" "}
          <Link to="/login" className="text-accent hover:underline">
            {t("login")}
          </Link>
        </p>
      </div>
    </div>
  );
}
