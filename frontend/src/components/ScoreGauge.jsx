export default function ScoreGauge({ score, size = 96 }) {
  const pct = Math.round((score || 0) * 100);

  // Color ramp: green → yellow → orange → red
  const color =
    pct >= 95 ? "#EF4444" :
    pct >= 90 ? "#F97316" :
    pct >= 80 ? "#F59E0B" :
               "#3B82F6";

  const r = size * 0.375;          // radius = 36 at size=96
  const strokeW = size * 0.0833;   // stroke = 8 at size=96
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const center = size / 2;

  return (
    <div
      className="relative inline-flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size }}
      title={`Match score: ${pct}%`}
    >
      <svg
        width={size}
        height={size}
        style={{ transform: "rotate(-90deg)" }}
      >
        {/* Track */}
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={strokeW}
        />
        {/* Progress arc */}
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={strokeW}
          strokeDasharray={circ}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{
            filter: `drop-shadow(0 0 6px ${color}80)`,
            transition: "stroke-dashoffset 0.6s ease, stroke 0.3s ease",
          }}
        />
      </svg>

      {/* Label */}
      <div
        className="absolute inset-0 flex flex-col items-center justify-center"
      >
        <span
          className="font-bold leading-none"
          style={{
            color,
            fontSize: size * 0.19,
            textShadow: `0 0 12px ${color}60`,
          }}
        >
          {pct}%
        </span>
        <span
          className="mt-0.5 font-medium uppercase tracking-wider"
          style={{
            color: "rgba(255,255,255,0.35)",
            fontSize: size * 0.1,
          }}
        >
          match
        </span>
      </div>
    </div>
  );
}
