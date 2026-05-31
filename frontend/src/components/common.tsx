import { useState } from "react";

import { useSim } from "../store/useSim";

export function Flag({ code, className = "h-4 w-6" }: { code: string; className?: string }) {
  const iso2 = useSim((s) => s.teams[code]?.iso2);
  const [err, setErr] = useState(false);
  if (!iso2 || err) {
    return (
      <span
        className={`inline-flex items-center justify-center rounded-[3px] bg-line text-[9px] font-semibold text-muted ${className}`}
      >
        {code}
      </span>
    );
  }
  return (
    <img
      src={`https://flagcdn.com/${iso2}.svg`}
      alt={code}
      loading="lazy"
      onError={() => setErr(true)}
      className={`rounded-[3px] object-cover ring-1 ring-black/40 ${className}`}
    />
  );
}

export function TeamName({ code, className = "" }: { code: string; className?: string }) {
  const name = useSim((s) => s.teams[code]?.name ?? code);
  return <span className={className}>{name}</span>;
}

export function pct(x: number): string {
  if (x >= 0.9995) return "100%";
  if (x < 0.0005) return "–";
  return `${(x * 100).toFixed(1)}%`;
}

export const STAGE_LABEL: Record<string, string> = {
  group: "Group Stage",
  R32: "Round of 32",
  R16: "Round of 16",
  QF: "Quarter-finals",
  SF: "Semi-finals",
  "3P": "Third-place play-off",
  F: "Final",
};
