import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const styles = {
  card: {
    maxWidth: 380,
    margin: "4rem auto",
    background: "#fff",
    borderRadius: 8,
    padding: "2rem",
    boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
    border: "1px solid #e0e0e0",
  } as React.CSSProperties,
  title: { marginBottom: "1.25rem", fontSize: "1.4rem" } as React.CSSProperties,
  field: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "0.3rem",
    marginBottom: "1rem",
  } as React.CSSProperties,
  label: { fontSize: "0.85rem", fontWeight: 500, color: "#555" } as React.CSSProperties,
  input: {
    padding: "0.55rem 0.7rem",
    border: "1px solid #ccc",
    borderRadius: 4,
    fontSize: "0.95rem",
    fontFamily: "inherit",
  } as React.CSSProperties,
  hint: { fontSize: "0.75rem", color: "#888", marginTop: "-0.5rem", marginBottom: "1rem" } as React.CSSProperties,
  error: {
    color: "#c0392b",
    background: "#fdecea",
    padding: "0.5rem 0.75rem",
    borderRadius: 4,
    fontSize: "0.85rem",
    marginBottom: "1rem",
  } as React.CSSProperties,
  btn: {
    width: "100%",
    padding: "0.6rem",
    border: "none",
    borderRadius: 4,
    background: "#1a73e8",
    color: "#fff",
    fontSize: "0.95rem",
    fontWeight: 600,
    cursor: "pointer",
  } as React.CSSProperties,
  btnDisabled: {
    background: "#a0b4d4",
    cursor: "not-allowed",
  } as React.CSSProperties,
  footer: {
    marginTop: "1.25rem",
    textAlign: "center" as const,
    fontSize: "0.85rem",
    color: "#666",
  } as React.CSSProperties,
};

export function Signup() {
  const { signup, loading, error, clearError } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();
    try {
      await signup(email, password);
      navigate("/upload", { replace: true });
    } catch {
      // error is surfaced via context
    }
  };

  return (
    <div style={styles.card}>
      <h1 style={styles.title}>Create account</h1>

      {error && <div style={styles.error}>{error}</div>}

      <form onSubmit={handleSubmit}>
        <div style={styles.field}>
          <label htmlFor="email" style={styles.label}>
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={styles.input}
          />
        </div>

        <div style={styles.field}>
          <label htmlFor="password" style={styles.label}>
            Password
          </label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={styles.input}
          />
        </div>
        <p style={styles.hint}>Must be at least 8 characters.</p>

        <button
          type="submit"
          disabled={loading}
          style={{ ...styles.btn, ...(loading ? styles.btnDisabled : {}) }}
        >
          {loading ? "Creating account…" : "Sign up"}
        </button>
      </form>

      <p style={styles.footer}>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
