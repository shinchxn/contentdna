import { Link, useLocation } from "react-router-dom";
import { Shield } from "lucide-react";

const links = [
  { to: "/",        label: "Dashboard" },
  { to: "/upload",  label: "Register" },
  { to: "/detect",  label: "Detect" },
  { to: "/hunt",    label: "Hunt" },
  { to: "/accounts",label: "Accounts" },
  { to: "/monitor", label: "Monitor" },
  { to: "/alerts",  label: "Alerts" },
];

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <nav
      className="sticky top-0 z-50 border-b border-white/10 px-6 py-3 flex items-center gap-8"
      style={{
        background: "rgba(15, 23, 42, 0.85)",
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
      }}
    >
      {/* Logo */}
      <Link
        to="/"
        className="flex items-center gap-2 font-bold text-xl select-none"
        style={{ color: "#3B82F6", textDecoration: "none" }}
      >
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{
            background: "linear-gradient(135deg, #3B82F6 0%, #10B981 100%)",
            boxShadow: "0 0 12px rgba(59,130,246,0.4)",
          }}
        >
          <Shield size={16} color="white" />
        </div>
        <span style={{ letterSpacing: "-0.5px" }}>ContentDNA</span>
      </Link>

      {/* Navigation links */}
      <div className="flex items-center gap-1">
        {links.map((l) => {
          const isActive = pathname === l.to;
          return (
            <Link
              key={l.to}
              to={l.to}
              className="px-3 py-1.5 rounded-lg text-sm font-medium"
              style={{
                color: isActive ? "#3B82F6" : "rgba(255,255,255,0.55)",
                background: isActive ? "rgba(59,130,246,0.12)" : "transparent",
                textDecoration: "none",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.color = "white";
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.color = "rgba(255,255,255,0.55)";
              }}
            >
              {l.label}
              {isActive && (
                <span
                  className="block mx-auto mt-0.5"
                  style={{
                    width: "16px",
                    height: "2px",
                    background: "#3B82F6",
                    borderRadius: "1px",
                    boxShadow: "0 0 6px #3B82F6",
                  }}
                />
              )}
            </Link>
          );
        })}
      </div>

      {/* Right side — live indicator */}
      <div className="ml-auto flex items-center gap-2">
        <span className="relative flex items-center gap-1.5 text-xs text-white/40">
          <span className="relative flex h-2 w-2">
            <span
              className="absolute inline-flex h-full w-full rounded-full opacity-75"
              style={{
                background: "#10B981",
                animation: "ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite",
              }}
            />
            <span
              className="relative inline-flex rounded-full h-2 w-2"
              style={{ background: "#10B981" }}
            />
          </span>
          Live
        </span>
      </div>

      <style>{`
        @keyframes ping {
          75%, 100% { transform: scale(2); opacity: 0; }
        }
      `}</style>
    </nav>
  );
}
