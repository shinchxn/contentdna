const config = {
  instagram: { label: "Instagram", color: "#EC4899", bg: "rgba(236,72,153,0.12)", icon: "📸" },
  youtube:   { label: "YouTube",   color: "#EF4444", bg: "rgba(239,68,68,0.12)",   icon: "▶" },
  tiktok:    { label: "TikTok",    color: "#22D3EE", bg: "rgba(34,211,238,0.12)",  icon: "🎵" },
  reddit:    { label: "Reddit",    color: "#F97316", bg: "rgba(249,115,22,0.12)",  icon: "🔴" },
  web:       { label: "Web",       color: "#60A5FA", bg: "rgba(96,165,250,0.12)",  icon: "🌐" },
  live:      { label: "Live",      color: "#34D399", bg: "rgba(52,211,153,0.12)",  icon: "📡" },
  twitter:   { label: "Twitter/X", color: "#94A3B8", bg: "rgba(148,163,184,0.12)", icon: "𝕏" },
};

export default function PlatformBadge({ platform }) {
  const c = config[platform?.toLowerCase()] || {
    label: platform || "Unknown",
    color: "rgba(255,255,255,0.6)",
    bg: "rgba(255,255,255,0.06)",
    icon: "?",
  };

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold"
      style={{
        color: c.color,
        background: c.bg,
        border: `1px solid ${c.color}30`,
      }}
    >
      <span style={{ fontSize: "10px" }}>{c.icon}</span>
      {c.label}
    </span>
  );
}
