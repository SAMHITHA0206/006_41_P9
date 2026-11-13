import { useMemo, useState } from "react";

const USERS_KEY = "smart-meter-users";
const CURRENT_USER_KEY = "smart-meter-current-user";

function getStoredUsers() {
  try {
    const raw = localStorage.getItem(USERS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export default function AuthPage({ onAuthSuccess }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const pageTitle = useMemo(
    () => (mode === "login" ? "Welcome back" : "Create your account"),
    [mode]
  );

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setError("");
    setSuccess("");
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const email = form.email.trim();
    const password = form.password.trim();
    const name = form.name.trim();

    if (!email || !password) {
      setError("Email and password are required.");
      return;
    }

    const users = getStoredUsers();

    if (mode === "signup") {
      if (!name) {
        setError("Full name is required to sign up.");
        return;
      }
      if (password.length < 6) {
        setError("Password must be at least 6 characters long.");
        return;
      }
      if (users.some((user) => user.email.toLowerCase() === email.toLowerCase())) {
        setError("An account with this email already exists.");
        return;
      }

      const newUser = {
        id: Date.now().toString(),
        name,
        email: email.toLowerCase(),
        password,
      };

      const updatedUsers = [...users, newUser];
      localStorage.setItem(USERS_KEY, JSON.stringify(updatedUsers));
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify({ id: newUser.id, name: newUser.name, email: newUser.email }));
      setSuccess("Account created successfully.");
      onAuthSuccess({ id: newUser.id, name: newUser.name, email: newUser.email });
      return;
    }

    const matchedUser = users.find(
      (user) => user.email.toLowerCase() === email.toLowerCase() && user.password === password
    );

    if (!matchedUser) {
      setError("Invalid email or password.");
      return;
    }

    const sessionUser = { id: matchedUser.id, name: matchedUser.name, email: matchedUser.email };
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(sessionUser));
    onAuthSuccess(sessionUser);
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-header">
          <div className="brand-badge">⚡</div>
          <h1>Smart Meter Reporter</h1>
        </div>

        <div className="mode-switch" aria-label="Authentication mode">
          <button
            type="button"
            className={mode === "login" ? "mode-btn active" : "mode-btn"}
            onClick={() => setMode("login")}
          >
            Login
          </button>
          <button
            type="button"
            className={mode === "signup" ? "mode-btn active" : "mode-btn"}
            onClick={() => setMode("signup")}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <h2>{pageTitle}</h2>

          {mode === "signup" && (
            <label className="field">
              <span>Full name</span>
              <input
                type="text"
                name="name"
                value={form.name}
                onChange={handleChange}
                placeholder="Your name"
              />
            </label>
          )}

          <label className="field">
            <span>Email</span>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="name@example.com"
            />
          </label>

          <label className="field">
            <span>Password</span>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder={mode === "login" ? "Enter your password" : "Create password (min 6 chars)"}
            />
          </label>

          {error && <div className="alert error">{error}</div>}
          {success && <div className="alert success">{success}</div>}

          <button type="submit" className="btn primary auth-submit">
            {mode === "login" ? "Login" : "Create account"}
          </button>
        </form>

        <div className="auth-note">
          <small>
            {mode === "login"
              ? "Need an account?"
              : "Already have an account?"}
            <button type="button" className="text-link" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
              {mode === "login" ? "Sign up" : "Login"}
            </button>
          </small>
        </div>
      </div>
    </div>
  );
}
