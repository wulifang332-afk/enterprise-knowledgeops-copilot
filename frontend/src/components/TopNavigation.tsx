import { NavLink } from "react-router-dom";

const routes = [
  { path: "/", label: "Landing" },
  { path: "/workspace", label: "Workspace" },
  { path: "/search", label: "Search" },
  { path: "/graph", label: "Graph" },
  { path: "/query", label: "Query" },
  { path: "/readiness", label: "Readiness" },
  { path: "/evaluation", label: "Evaluation" },
  { path: "/governance", label: "Governance" }
];

export function TopNavigation() {
  return (
    <nav className="top-nav" aria-label="Primary navigation">
      {routes.map((route) => (
        <NavLink
          key={route.path}
          to={route.path}
          className={({ isActive }) =>
            isActive ? "top-nav__link top-nav__link--active" : "top-nav__link"
          }
          end={route.path === "/"}
        >
          {route.label}
        </NavLink>
      ))}
    </nav>
  );
}
