import SeverityBadge from "./SeverityBadge";
import PlatformBadge from "./PlatformBadge";
import ScoreGauge from "./ScoreGauge";
import { ExternalLink, ShieldCheck, Clock } from "lucide-react";

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export default function AlertCard({ alert }) {
  return (
    <div
      className="rounded-2xl p-5 flex gap-5 fade-in"
      style={{
        background: "rgba(30,41,59,0.6)",
        border: "1px solid rgba(255,255,255,0.08)",
        backdropFilter: "blur(8px)",
        transition: "border-color 0.2s ease, box-shadow 0.2s ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(59,130,246,0.3)";
        e.currentTarget.style.boxShadow = "0 0 24px rgba(59,130,246,0.08)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
        e.currentTarget.style.boxShadow = "none";
      }}
    >
      {/* Thumbnail */}
      {alert.thumbnail_url && (
        <div className="flex-shrink-0">
          <img
            src={alert.thumbnail_url}
            alt="match thumbnail"
            className="w-20 h-20 rounded-xl object-cover"
            style={{ border: "1px solid rgba(255,255,255,0.1)" }}
            onError={(e) => { e.currentTarget.style.display = "none"; }}
          />
        </div>
      )}

      {/* Score gauge */}
      <div className="flex-shrink-0 self-center">
        <ScoreGauge score={alert.match_score || 0} size={80} />
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0 space-y-2">
        {/* Badges row */}
        <div className="flex items-center gap-2 flex-wrap">
          <SeverityBadge severity={alert.severity} />
          <PlatformBadge platform={alert.platform} />
          {alert.watermark_confirmed && (
            <span
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold"
              style={{
                color: "#10B981",
                background: "rgba(16,185,129,0.12)",
                border: "1px solid rgba(16,185,129,0.3)",
              }}
            >
              <ShieldCheck size={11} />
              Watermark Confirmed
            </span>
          )}
        </div>

        {/* Source URL */}
        {alert.source_url && (
          <a
            href={alert.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm hover:underline truncate"
            style={{ color: "#60A5FA", maxWidth: "100%" }}
          >
            <span className="truncate">{alert.source_url}</span>
            <ExternalLink size={11} className="flex-shrink-0" />
          </a>
        )}

        {/* Page URL (where found) */}
        {alert.page_url && alert.page_url !== alert.source_url && (
          <p className="text-xs truncate" style={{ color: "rgba(255,255,255,0.35)" }}>
            Found on: {alert.page_url}
          </p>
        )}

        {/* Asset title */}
        {alert.asset_title && (
          <p className="text-xs" style={{ color: "rgba(255,255,255,0.5)" }}>
            Matches: <span className="text-white/70 font-medium">{alert.asset_title}</span>
          </p>
        )}

        {/* Timestamp */}
        <div className="flex items-center gap-1 text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
          <Clock size={11} />
          <span title={new Date(alert.created_at).toLocaleString()}>
            {timeAgo(alert.created_at)} · {new Date(alert.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
}
