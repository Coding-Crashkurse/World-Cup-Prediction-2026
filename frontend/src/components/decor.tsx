import { useId } from "react";

function pentagon(cx: number, cy: number, r: number, rotDeg = 0): string {
  return Array.from({ length: 5 }, (_, i) => {
    const a = ((-90 + rotDeg + i * 72) * Math.PI) / 180;
    return `${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`;
  }).join(" ");
}

// A stylized soccer ball, geometry computed so it always renders cleanly.
export function SoccerBall({ className = "h-5 w-5" }: { className?: string }) {
  const clip = useId();
  const C = 32;
  const R = 30;
  const central = pentagon(C, C, 10);
  const seams = Array.from({ length: 5 }, (_, i) => {
    const a = ((-90 + i * 72) * Math.PI) / 180;
    return {
      x1: C + 10 * Math.cos(a),
      y1: C + 10 * Math.sin(a),
      x2: C + R * 0.99 * Math.cos(a),
      y2: C + R * 0.99 * Math.sin(a),
    };
  });
  const outers = Array.from({ length: 5 }, (_, i) => {
    const aDeg = -90 + 36 + i * 72;
    const a = (aDeg * Math.PI) / 180;
    return pentagon(C + R * 0.74 * Math.cos(a), C + R * 0.74 * Math.sin(a), 7.5, aDeg + 90);
  });

  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden="true">
      <defs>
        <clipPath id={clip}>
          <circle cx={C} cy={C} r={R} />
        </clipPath>
      </defs>
      <circle cx={C} cy={C} r={R} fill="#f5f7fc" stroke="#0a0e1a" strokeWidth={1.5} />
      <g clipPath={`url(#${clip})`} fill="#0a0e1a" stroke="#0a0e1a" strokeLinejoin="round">
        <polygon points={central} strokeWidth={1} />
        {outers.map((p, i) => (
          <polygon key={i} points={p} strokeWidth={1} />
        ))}
        {seams.map((s, i) => (
          <line key={i} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2} strokeWidth={1.4} />
        ))}
      </g>
    </svg>
  );
}

// Faint football-pitch markings, used as a full-bleed backdrop.
export function PitchLines({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 1050 680"
      preserveAspectRatio="xMidYMid slice"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <rect x="12" y="12" width="1026" height="656" rx="6" />
      <line x1="525" y1="12" x2="525" y2="668" />
      <circle cx="525" cy="340" r="92" />
      <circle cx="525" cy="340" r="4" fill="currentColor" />
      <rect x="12" y="170" width="165" height="340" />
      <rect x="12" y="250" width="60" height="180" />
      <rect x="873" y="170" width="165" height="340" />
      <rect x="978" y="250" width="60" height="180" />
      <path d="M177 250 A92 92 0 0 1 177 430" />
      <path d="M873 250 A92 92 0 0 0 873 430" />
    </svg>
  );
}
