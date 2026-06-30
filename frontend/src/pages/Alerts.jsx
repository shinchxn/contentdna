import { useState, useEffect } from "react";
import AlertCard from "../components/AlertCard";
import api from "../lib/api";
import { supabase } from "../lib/supabase";
import { Filter, RefreshCw, Bell } from "lucide-react";

const OWNER_ID = "1c13b877-829b-4f5b-9b0f-058b24dc5c4d";
const PLATFORMS  = ["instagram", "youtube", "tiktok", "reddit", "web", "live"];
const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM"];

export default function Alerts() {
  const [alerts, setAlerts]     = useState([]);
  const [platform, setPlatform] = useState("");
  const [severity, setSeverity] = useState("");
  const [loading, setLoading]   = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAlerts = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    try {
      const params = new URLSearchParams({ owner_id: OWNER_ID, limit: "50" });
      if (platform) params.append("platform", platform);
      if (severity) params.append("severity", severity);
      const res = await api.get(`/alerts?${params}`);
      setAlerts(res.data);
    } catch {
      // silently fail — alerts list stays at last known state
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchAlerts(); }, [platform, severity]);

  // Supabase Realtime — prepend new alerts as they arrive
  useEffect(() => {
    const channel = supabase
      .channel("all-alerts-feed")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "alerts" },
        (payload) => {
          setAlerts((prev) => {
            // Only show if it matches current filters
            const a = payload.new;
            if (platform && a.platform !== platform) return prev;
            if (severity && a.severity !== severity) return prev;
            return [a, ...prev];
          });
        }
      )
      .subscribe();
    return () => supabase.removeChannel(channel);
  }, [platform, severity]);

  const criticalCount = alerts.filter((a) => a.severity === "CRITICAL").length;

  return (
    <div className="space-y-6 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white" style={{ letterSpacing: "-0.5px" }}>
            Violations
          </h1>
          <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.45)" }}>
            All detected content violations · Updated in real time
          </p>
        </div>
        <div className="flex items-center gap-3">
          {criticalCount > 0 && (
            <div
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold"
              style={{
                background: "rgba(239,68,68,0.15)",
                border: "1px solid rgba(239,68,68,0.3)",
                color: "#EF4444",
              }}
            >
              <Bell size={11} />
              {criticalCount} critical
            </div>
          )}
          <span
            className="px-3 py-1.5 rounded-full text-xs font-medium"
            style={{ background: "rgba(255,255,255,0.06)", color: "rgba(255,255,255,0.5)" }}
          >
            {alerts.length} total
          </span>
          <button
            onClick={() => fetchAlerts(true)}
            disabled={refreshing}
            className="p-2 rounded-xl"
            style={{
              background: "rgba(59,130,246,0.1)",
              border: "1px solid rgba(59,130,246,0.2)",
              color: "#60A5FA",
              cursor: "pointer",
            }}
            title="Refresh"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div
        className="rounded-xl p-4 flex flex-wrap gap-4 items-center"
        style={{
          background: "rgba(30,41,59,0.6)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <div className="flex items-center gap-2 text-xs font-medium" style={{ color: "rgba(255,255,255,0.5)" }}>
          <Filter size={13} />
          Filters
        </div>

        {/* Platform filter */}
        <div className="flex gap-1 flex-wrap">
          <button
            onClick={() => setPlatform("")}
            className="px-3 py-1 rounded-lg text-xs font-medium"
            style={{
              background: !platform ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.05)",
              border: !platform ? "1px solid rgba(59,130,246,0.4)" : "1px solid rgba(255,255,255,0.1)",
              color: !platform ? "#60A5FA" : "rgba(255,255,255,0.45)",
            }}
          >
            All Platforms
          </button>
          {PLATFORMS.map((p) => (
            <button
              key={p}
              onClick={() => setPlatform(p === platform ? "" : p)}
              className="px-3 py-1 rounded-lg text-xs font-medium capitalize"
              style={{
                background: platform === p ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.05)",
                border: platform === p ? "1px solid rgba(59,130,246,0.4)" : "1px solid rgba(255,255,255,0.1)",
                color: platform === p ? "#60A5FA" : "rgba(255,255,255,0.45)",
              }}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Divider */}
        <div style={{ width: "1px", height: "24px", background: "rgba(255,255,255,0.1)" }} />

        {/* Severity filter */}
        <div className="flex gap-1 flex-wrap">
          <button
            onClick={() => setSeverity("")}
            className="px-3 py-1 rounded-lg text-xs font-medium"
            style={{
              background: !severity ? "rgba(59,130,246,0.2)" : "rgba(255,255,255,0.05)",
              border: !severity ? "1px solid rgba(59,130,246,0.4)" : "1px solid rgba(255,255,255,0.1)",
              color: !severity ? "#60A5FA" : "rgba(255,255,255,0.45)",
            }}
          >
            All Severities
          </button>
          {SEVERITIES.map((s) => {
            const colors = {
              CRITICAL: { active: "rgba(239,68,68,0.2)", border: "rgba(239,68,68,0.4)", text: "#EF4444" },
              HIGH:     { active: "rgba(249,115,22,0.2)", border: "rgba(249,115,22,0.4)", text: "#F97316" },
              MEDIUM:   { active: "rgba(234,179,8,0.2)", border: "rgba(234,179,8,0.4)", text: "#EAB308" },
            };
            const c = colors[s];
            return (
              <button
                key={s}
                onClick={() => setSeverity(s === severity ? "" : s)}
                className="px-3 py-1 rounded-lg text-xs font-bold"
                style={{
                  background: severity === s ? c.active : "rgba(255,255,255,0.05)",
                  border: severity === s ? `1px solid ${c.border}` : "1px solid rgba(255,255,255,0.1)",
                  color: severity === s ? c.text : "rgba(255,255,255,0.45)",
                }}
              >
                {s}
              </button>
            );
          })}
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="flex items-center justify-center py-16 gap-3">
          <div
            className="w-7 h-7 rounded-full border-2 animate-spin"
            style={{ borderColor: "#3B82F6", borderTopColor: "transparent" }}
          />
          <span style={{ color: "rgba(255,255,255,0.4)", fontSize: "14px" }}>Loading violations…</span>
        </div>
      ) : alerts.length === 0 ? (
        <div
          className="rounded-2xl p-12 text-center"
          style={{
            background: "rgba(16,185,129,0.05)",
            border: "1px solid rgba(16,185,129,0.15)",
          }}
        >
          <p className="text-3xl mb-3">✅</p>
          <p className="font-semibold text-lg" style={{ color: "#10B981" }}>No violations found</p>
          <p className="text-sm mt-2" style={{ color: "rgba(255,255,255,0.35)" }}>
            {platform || severity
              ? "No violations match your current filters."
              : "Your content is clean across all monitored platforms."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((a) => (
            <AlertCard key={a.id} alert={a} />
          ))}
        </div>
      )}
    </div>
  );
}
