import { useState, useEffect } from "react";
import api from "../lib/api";
import { RefreshCw, Activity, Clock } from "lucide-react";

const OWNER_ID = "1c13b877-829b-4f5b-9b0f-058b24dc5c4d";

const PLATFORMS = [
  {
    id: "instagram",
    label: "Instagram",
    icon: "📸",
    desc: "Hashtag scanner · instagrapi",
    borderColor: "rgba(236,72,153,0.25)",
    glowColor: "rgba(236,72,153,0.1)",
    dotColor: "#EC4899",
  },
  {
    id: "youtube",
    label: "YouTube",
    icon: "▶",
    desc: "Data API v3 + yt-dlp thumbnails",
    borderColor: "rgba(239,68,68,0.25)",
    glowColor: "rgba(239,68,68,0.1)",
    dotColor: "#EF4444",
  },
  {
    id: "tiktok",
    label: "TikTok",
    icon: "🎵",
    desc: "gallery-dl hashtag crawler",
    borderColor: "rgba(34,211,238,0.25)",
    glowColor: "rgba(34,211,238,0.1)",
    dotColor: "#22D3EE",
  },
  {
    id: "reddit",
    label: "Reddit",
    icon: "🔴",
    desc: "PRAW · 9 sports subreddits",
    borderColor: "rgba(249,115,22,0.25)",
    glowColor: "rgba(249,115,22,0.1)",
    dotColor: "#F97316",
  },
];

function PlatformCard({ platform, onTrigger }) {
  const [status, setStatus] = useState("idle"); // idle | triggering | done | error

  const trigger = async () => {
    setStatus("triggering");
    try {
      await onTrigger(platform.id);
      setStatus("done");
      setTimeout(() => setStatus("idle"), 4000);
    } catch {
      setStatus("error");
      setTimeout(() => setStatus("idle"), 3000);
    }
  };

  const btnLabel =
    status === "triggering" ? "Triggering…" :
    status === "done"       ? "Triggered ✓" :
    status === "error"      ? "Error ✗" :
    "Trigger Now";

  const btnColor =
    status === "done"  ? "#10B981" :
    status === "error" ? "#EF4444" :
    "#60A5FA";

  return (
    <div
      className="rounded-2xl p-5 space-y-4 relative overflow-hidden"
      style={{
        background: `linear-gradient(135deg, rgba(30,41,59,0.9) 0%, ${platform.glowColor} 100%)`,
        border: `1px solid ${platform.borderColor}`,
        backdropFilter: "blur(8px)",
      }}
    >
      {/* Corner glow */}
      <div
        className="absolute -top-6 -right-6 w-24 h-24 rounded-full opacity-30"
        style={{ background: platform.dotColor, filter: "blur(24px)" }}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span
            className="text-2xl w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "rgba(255,255,255,0.06)" }}
          >
            {platform.icon}
          </span>
          <div>
            <p className="font-semibold text-white">{platform.label}</p>
            <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
              {platform.desc}
            </p>
          </div>
        </div>

        {/* Live indicator */}
        <div className="flex items-center gap-1.5">
          <span
            className="w-2 h-2 rounded-full"
            style={{
              background: platform.dotColor,
              boxShadow: `0 0 6px ${platform.dotColor}`,
              animation: "ping 2s infinite",
            }}
          />
          <span className="text-xs" style={{ color: "rgba(255,255,255,0.35)" }}>active</span>
        </div>
      </div>

      {/* Schedule info */}
      <div className="flex items-center gap-2 text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
        <Clock size={11} />
        Runs automatically every 15 minutes via Celery beat
      </div>

      {/* Trigger button */}
      <button
        onClick={trigger}
        disabled={status === "triggering"}
        className="w-full py-2 rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
        style={{
          background: "rgba(255,255,255,0.06)",
          border: `1px solid ${btnColor}30`,
          color: btnColor,
          cursor: status === "triggering" ? "wait" : "pointer",
          transition: "all 0.2s ease",
        }}
        onMouseEnter={(e) => { if (status === "idle") e.currentTarget.style.background = "rgba(255,255,255,0.1)"; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.06)"; }}
      >
        {status === "triggering" ? (
          <RefreshCw size={13} className="animate-spin" />
        ) : (
          <Activity size={13} />
        )}
        {btnLabel}
      </button>

      <style>{`@keyframes ping { 75%,100% { transform: scale(2); opacity: 0; } }`}</style>
    </div>
  );
}

export default function Monitor() {
  const [lastTrigger, setLastTrigger] = useState({});

  const handleTrigger = async (platformId) => {
    await api.post(`/hunt/${platformId}`, { owner_id: OWNER_ID });
    setLastTrigger((prev) => ({
      ...prev,
      [platformId]: new Date().toLocaleTimeString(),
    }));
  };

  return (
    <div className="space-y-8 fade-in">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white" style={{ letterSpacing: "-0.5px" }}>
          Platform Monitor
        </h1>
        <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.45)" }}>
          Platform-specific crawlers run every 15 minutes. Trigger manually for immediate sweeps.
        </p>
      </div>

      {/* Status overview */}
      <div
        className="rounded-2xl px-5 py-4 flex items-center gap-3"
        style={{
          background: "rgba(16,185,129,0.07)",
          border: "1px solid rgba(16,185,129,0.2)",
        }}
      >
        <div
          className="w-2 h-2 rounded-full"
          style={{ background: "#10B981", boxShadow: "0 0 8px #10B981", animation: "ping 2s infinite" }}
        />
        <p className="text-sm font-medium" style={{ color: "#34D399" }}>
          All crawlers operational · Celery beat scheduler running
        </p>
        <style>{`@keyframes ping { 75%,100% { transform: scale(2); opacity: 0; } }`}</style>
      </div>

      {/* Platform grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PLATFORMS.map((p) => (
          <PlatformCard key={p.id} platform={p} onTrigger={handleTrigger} />
        ))}
      </div>

      {/* Last triggered log */}
      {Object.keys(lastTrigger).length > 0 && (
        <div
          className="rounded-xl p-4 space-y-2 fade-in"
          style={{ background: "rgba(30,41,59,0.6)", border: "1px solid rgba(255,255,255,0.08)" }}
        >
          <p className="text-xs font-semibold" style={{ color: "rgba(255,255,255,0.5)" }}>
            Manual Trigger Log
          </p>
          {Object.entries(lastTrigger).map(([id, time]) => (
            <p key={id} className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>
              <span style={{ color: "rgba(255,255,255,0.7)" }} className="font-medium capitalize">
                {id}
              </span>{" "}
              — triggered at {time}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
