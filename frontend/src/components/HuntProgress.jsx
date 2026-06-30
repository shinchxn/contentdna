import { useEffect, useState } from "react";
import api from "../lib/api";
import { CheckCircle, XCircle, Loader2, FileSearch } from "lucide-react";

export default function HuntProgress({ jobId, onComplete }) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const res = await api.get(`/hunt/status/${jobId}`);
        setJob(res.data);
        if (res.data.status === "done" || res.data.status === "failed") {
          onComplete?.(res.data);
          return true; // stop polling
        }
      } catch (e) {
        setError("Failed to fetch job status");
        return true; // stop polling on error
      }
      return false;
    };

    let interval;
    poll().then((done) => {
      if (!done) {
        interval = setInterval(async () => {
          const done = await poll();
          if (done) clearInterval(interval);
        }, 2000);
      }
    });

    return () => clearInterval(interval);
  }, [jobId]);

  if (!job && !error) return null;

  if (error) {
    return (
      <div
        className="rounded-xl p-4 flex items-center gap-2"
        style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)" }}
      >
        <XCircle size={16} color="#EF4444" />
        <span className="text-sm" style={{ color: "#EF4444" }}>{error}</span>
      </div>
    );
  }

  const isDone   = job.status === "done";
  const isFailed = job.status === "failed";

  // Estimate progress — use pages_crawled / max_pages if available, else simulate
  const crawled = job.pages_crawled || 0;
  const maxPages = job.max_pages || 100;
  const pct = isDone ? 100 : Math.min(95, Math.round((crawled / maxPages) * 100));

  const barColor = isFailed ? "#EF4444" : isDone ? "#10B981" : "#3B82F6";

  return (
    <div
      className="rounded-2xl p-5 space-y-4 fade-in"
      style={{
        background: "rgba(30,41,59,0.7)",
        border: `1px solid ${isDone ? "rgba(16,185,129,0.25)" : isFailed ? "rgba(239,68,68,0.25)" : "rgba(59,130,246,0.2)"}`,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isDone ? (
            <CheckCircle size={18} color="#10B981" />
          ) : isFailed ? (
            <XCircle size={18} color="#EF4444" />
          ) : (
            <Loader2 size={18} color="#3B82F6" className="animate-spin" />
          )}
          <span className="font-semibold text-sm text-white">
            {isDone ? "Hunt Complete" : isFailed ? "Hunt Failed" : "Hunting..."}
          </span>
          <span
            className="font-mono text-xs px-2 py-0.5 rounded"
            style={{ color: "rgba(255,255,255,0.4)", background: "rgba(255,255,255,0.06)" }}
          >
            {jobId.substring(0, 8)}…
          </span>
        </div>
        <span className="text-sm font-bold" style={{ color: barColor }}>{pct}%</span>
      </div>

      {/* Progress bar */}
      <div
        className="w-full rounded-full overflow-hidden"
        style={{ height: "6px", background: "rgba(255,255,255,0.08)" }}
      >
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: barColor,
            boxShadow: `0 0 8px ${barColor}80`,
            transition: "width 0.5s ease",
          }}
        />
      </div>

      {/* Stats */}
      <div className="flex gap-6 text-xs" style={{ color: "rgba(255,255,255,0.45)" }}>
        <span className="flex items-center gap-1">
          <FileSearch size={12} />
          {crawled.toLocaleString()} pages
        </span>
        <span>🖼 {(job.media_found || 0).toLocaleString()} media</span>
        <span
          className="font-bold"
          style={{ color: (job.matches_found || 0) > 0 ? "#EF4444" : undefined }}
        >
          ⚠️ {(job.matches_found || 0)} matches
        </span>
        {job.current_url && (
          <span className="truncate max-w-xs hidden md:block">
            → {job.current_url}
          </span>
        )}
      </div>
    </div>
  );
}
