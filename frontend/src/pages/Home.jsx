import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell,
} from "recharts";
import AlertCard from "../components/AlertCard";
import api from "../lib/api";
import { TrendingUp, Shield, AlertTriangle, Activity, RefreshCw } from "lucide-react";

const OWNER_ID = "demo-owner-id";

const PLATFORM_COLORS = {
  instagram: "#EC4899",
  youtube:   "#EF4444",
  tiktok:    "#22D3EE",
  reddit:    "#F97316",
  web:       "#60A5FA",
  live:      "#34D399",
};

function StatCard({ label, value, color, icon: Icon, sublabel }) {
  return (
    <div
      className="rounded-2xl p-5 space-y-1 relative overflow-hidden"
      style={{
        background: "rgba(30,41,59,0.7)",
        border: "1px solid rgba(255,255,255,0.08)",
        backdropFilter: "blur(8px)",
      }}
    >
      {/* Glow blob */}
      <div
        className="absolute -top-4 -right-4 w-20 h-20 rounded-full opacity-20"
        style={{ background: color, filter: "blur(20px)" }}
      />
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium" style={{ color: "rgba(255,255,255,0.5)" }}>
          {label}
        </p>
        <Icon size={18} style={{ color, opacity: 0.8 }} />
      </div>
      <p className="text-4xl font-bold" style={{ color }}>
        {value ?? "—"}
      </p>
      {sublabel && (
        <p className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
          {sublabel}
        </p>
      )}
    </div>
  );
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      className="px-3 py-2 rounded-xl text-sm"
      style={{ background: "#1E293B", border: "1px solid rgba(255,255,255,0.12)" }}
    >
      <p className="font-semibold text-white capitalize">{label}</p>
      <p style={{ color: "#60A5FA" }}>{payload[0].value} violations</p>
    </div>
  );
};

export default function Home() {
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = async () => {
    try {
      const res = await api.get(`/stats?owner_id=${OWNER_ID}`);
      setStats(res.data);
      setError(null);
    } catch (e) {
      setError("Could not reach API — is the backend running on :8000?");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); }, []);

  const refresh = () => { setRefreshing(true); load(); };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 gap-3">
        <div
          className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
          style={{ borderColor: "#3B82F6", borderTopColor: "transparent" }}
        />
        <span style={{ color: "rgba(255,255,255,0.5)" }}>Loading dashboard…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-2xl p-8 text-center space-y-3"
        style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)" }}
      >
        <p className="text-lg font-semibold" style={{ color: "#EF4444" }}>⚠️ {error}</p>
        <p style={{ color: "rgba(255,255,255,0.4)", fontSize: "14px" }}>
          The frontend is fully operational. Connect the backend to see live data.
        </p>
        <button
          onClick={refresh}
          className="px-4 py-2 rounded-lg text-sm font-medium"
          style={{ background: "rgba(239,68,68,0.15)", color: "#EF4444", border: "1px solid rgba(239,68,68,0.3)" }}
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const platformData = Object.entries(stats?.alerts_by_platform || {}).map(([k, v]) => ({
    name: k,
    count: v,
    color: PLATFORM_COLORS[k] || "#60A5FA",
  }));

  return (
    <div className="space-y-8 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white" style={{ letterSpacing: "-0.5px" }}>
            Dashboard
          </h1>
          <p style={{ color: "rgba(255,255,255,0.45)", fontSize: "14px", marginTop: "4px" }}>
            Real-time content protection overview
          </p>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium"
          style={{
            background: "rgba(59,130,246,0.1)",
            border: "1px solid rgba(59,130,246,0.25)",
            color: "#60A5FA",
          }}
        >
          <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Protected Assets"
          value={stats?.total_assets ?? 0}
          color="#3B82F6"
          icon={Shield}
          sublabel="fingerprinted files"
        />
        <StatCard
          label="Total Violations"
          value={stats?.total_alerts ?? 0}
          color="#F59E0B"
          icon={AlertTriangle}
          sublabel="all time"
        />
        <StatCard
          label="Critical Alerts"
          value={stats?.alerts_by_severity?.CRITICAL ?? 0}
          color="#EF4444"
          icon={TrendingUp}
          sublabel="≥95% match score"
        />
        <StatCard
          label="Active Hunts"
          value={stats?.active_hunt_jobs ?? 0}
          color="#10B981"
          icon={Activity}
          sublabel="running now"
        />
      </div>

      {/* Chart */}
      {platformData.length > 0 && (
        <div
          className="rounded-2xl p-6"
          style={{
            background: "rgba(30,41,59,0.7)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <h2 className="font-semibold text-white mb-5">Violations by Platform</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={platformData} barSize={36}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.05)"
                vertical={false}
              />
              <XAxis
                dataKey="name"
                tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12, fontFamily: "Inter" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 12, fontFamily: "Inter" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {platformData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Recent alerts */}
      <div>
        <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
          Recent Violations
          {stats?.recent_alerts?.length > 0 && (
            <span
              className="px-2 py-0.5 rounded-full text-xs font-bold"
              style={{ background: "rgba(239,68,68,0.15)", color: "#EF4444" }}
            >
              {stats.recent_alerts.length}
            </span>
          )}
        </h2>
        {!stats?.recent_alerts?.length ? (
          <div
            className="rounded-2xl p-10 text-center"
            style={{ background: "rgba(16,185,129,0.06)", border: "1px solid rgba(16,185,129,0.15)" }}
          >
            <p className="text-2xl mb-2">✅</p>
            <p className="font-semibold" style={{ color: "#10B981" }}>No violations detected</p>
            <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.35)" }}>
              Your content is clean across all monitored platforms.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {stats.recent_alerts.map((a) => (
              <AlertCard key={a.id} alert={a} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
