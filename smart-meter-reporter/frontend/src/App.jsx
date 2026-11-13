import React, { useEffect, useMemo, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import SubmitReport from "./pages/SubmitReport.jsx";
import UserDashboard from "./pages/UserDashboard.jsx";
import HandlerDashboard from "./pages/HandlerDashboard.jsx";
import RoutingDashboard from "./pages/RoutingDashboard.jsx";
import Analytics from "./pages/Analytics.jsx";
import AuthPage from "./pages/AuthPage.jsx";

const CURRENT_USER_KEY = "smart-meter-current-user";

const links = [
  ["/", "Submit Report"],
  ["/track", "My Reports"],
  ["/handler", "Handler"],
  ["/routing", "Routing"],
  ["/analytics", "Analytics"],
];

function getCurrentUser() {
  try {
    const raw = localStorage.getItem(CURRENT_USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => getCurrentUser());

  useEffect(() => {
    if (currentUser) {
      localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(currentUser));
    } else {
      localStorage.removeItem(CURRENT_USER_KEY);
    }
  }, [currentUser]);

  const userName = useMemo(() => currentUser?.name || "User", [currentUser]);

  const handleLogout = () => {
    setCurrentUser(null);
  };

  if (!currentUser) {
    return <AuthPage onAuthSuccess={setCurrentUser} />;
  }

  return (
    <>
      <header className="topbar">
        <div className="brand">⚡ Smart Meter Anomaly Reporter</div>
        <nav>
          {links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="user-menu">
          <span className="user-pill">{userName}</span>
          <button type="button" className="btn small logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<SubmitReport />} />
          <Route path="/track" element={<UserDashboard />} />
          <Route path="/handler" element={<HandlerDashboard />} />
          <Route path="/routing" element={<RoutingDashboard />} />
          <Route path="/analytics" element={<Analytics />} />
        </Routes>
      </main>
    </>
  );
}
