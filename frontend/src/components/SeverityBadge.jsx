const config = {
  CRITICAL: {
    cls: "text-red-400",
    bg: "rgba(239,68,68,0.12)",
    border: "rgba(239,68,68,0.35)",
    glow: "0 0 8px rgba(239,68,68,0.3)",
  },
  HIGH: {
    cls: "text-orange-400",
    bg: "rgba(249,115,22,0.12)",
    border: "rgba(249,115,22,0.35)",
    glow: "0 0 8px rgba(249,115,22,0.3)",
  },
  MEDIUM: {
    cls: "text-yellow-400",
    bg: "rgba(234,179,8,0.12)",
    border: "rgba(234,179,8,0.35)",
    glow: "none",
  },
  LOW: {
    cls: "text-blue-400",
    bg: "rgba(59,130,246,0.12)",
    border: "rgba(59,130,246,0.35)",
    glow: "none",
  },
};

export default function SeverityBadge({ severity }) {
  const c = config[severity] || {
    cls: "text-white/50",
    bg: "rgba(255,255,255,0.06)",
    border: "rgba(255,255,255,0.15)",
    glow: "none",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold tracking-wide ${c.cls}`}
      style={{
        background: c.bg,
        border: `1px solid ${c.border}`,
        boxShadow: c.glow,
        letterSpacing: "0.05em",
      }}
    >
      {severity}
    </span>
  );
}
