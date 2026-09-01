import { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const navLinkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  textDecoration: "none",
  color: isActive ? "#1a73e8" : "#444",
  fontWeight: isActive ? 600 : 400,
  padding: "0.25rem 0.5rem",
  borderRadius: 4,
  background: isActive ? "#e8f0fe" : "transparent",
});

const styles = {
  shell: {
    fontFamily: "system-ui, -apple-system, sans-serif",
    minHeight: "100vh",
    background: "#f5f6f8",
  } as React.CSSProperties,
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0.75rem 1.5rem",
    background: "#fff",
    borderBottom: "1px solid #e0e0e0",
    boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
  } as React.CSSProperties,
  nav: {
    display: "flex",
    gap: "0.25rem",
    alignItems: "center",
  } as React.CSSProperties,
  brand: {
    fontSize: "1.1rem",
    fontWeight: 700,
    color: "#222",
  } as React.CSSProperties,
  main: {
    maxWidth: 960,
    margin: "0 auto",
    padding: "2rem 1.5rem",
  } as React.CSSProperties,
  logoutBtn: {
    border: "1px solid #d0d0d0",
    background: "#fff",
    borderRadius: 4,
    padding: "0.35rem 0.75rem",
    cursor: "pointer",
    fontSize: "0.85rem",
    color: "#555",
  } as React.CSSProperties,
};

export function Layout({ children }: { children: ReactNode }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div style={styles.shell}>
      <header style={styles.header}>
        <span style={styles.brand}>Recon Dashboard</span>
        <nav style={styles.nav}>
          <NavLink to="/upload" style={navLinkStyle}>
            Upload
          </NavLink>
          <NavLink to="/dashboard" style={navLinkStyle}>
            Dashboard
          </NavLink>
          <button onClick={handleLogout} style={styles.logoutBtn}>
            Log out
          </button>
        </nav>
      </header>
      <main style={styles.main}>{children}</main>
    </div>
  );
}
