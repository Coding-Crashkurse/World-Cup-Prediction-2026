import * as d3 from "d3";
import { useEffect, useMemo, useState } from "react";

import { fetchEloHistory } from "../api/client";
import type { EloHistory as EloHistoryData } from "../api/types";
import { useSim } from "../store/useSim";
import { SoccerBall } from "./decor";

const W = 1000;
const H = 560;
const M = { top: 24, right: 104, bottom: 30, left: 46 };
const IW = W - M.left - M.right;
const IH = H - M.top - M.bottom;
const TOP_COLORS = [
  "#c8ff35",
  "#22d3c7",
  "#2f6df0",
  "#f59e0b",
  "#ec4899",
  "#a78bfa",
  "#43e08a",
  "#fb7185",
];

export function EloHistory() {
  const teams = useSim((s) => s.teams);
  const model = useSim((s) => s.model);
  const reset = useSim((s) => s.reset);
  const [data, setData] = useState<EloHistoryData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drawn, setDrawn] = useState(false);
  const [runId, setRunId] = useState(0);

  useEffect(() => {
    fetchEloHistory()
      .then(setData)
      .catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (!data) return;
    setDrawn(false);
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setDrawn(true)));
    return () => cancelAnimationFrame(id);
  }, [data, runId]);

  const chart = useMemo(() => {
    if (!data || Object.keys(data.series).length === 0) return null;
    const parsed: Record<string, [Date, number][]> = {};
    let minD = Infinity;
    let maxD = -Infinity;
    let minE = Infinity;
    let maxE = -Infinity;
    for (const [code, pts] of Object.entries(data.series)) {
      const arr = pts.map(([d, e]) => [new Date(d), e] as [Date, number]);
      parsed[code] = arr;
      for (const [d, e] of arr) {
        minD = Math.min(minD, +d);
        maxD = Math.max(maxD, +d);
        minE = Math.min(minE, e);
        maxE = Math.max(maxE, e);
      }
    }
    const x = d3.scaleTime().domain([new Date(minD), new Date(maxD)]).range([0, IW]);
    const y = d3.scaleLinear().domain([minE - 20, maxE + 20]).range([IH, 0]).nice();
    const line = d3
      .line<[Date, number]>()
      .x((d) => x(d[0]))
      .y((d) => y(d[1]))
      .curve(d3.curveMonotoneX);
    const lastElo = (c: string) => parsed[c][parsed[c].length - 1][1];
    const ranked = Object.keys(parsed).sort((a, b) => lastElo(b) - lastElo(a));
    const topCodes = ranked.slice(0, 8);
    const colorOf = (c: string) => {
      const i = topCodes.indexOf(c);
      return i >= 0 ? TOP_COLORS[i] : "rgba(140,165,151,0.18)";
    };
    return { parsed, x, y, line, ranked, topCodes, colorOf, lastElo };
  }, [data]);

  return (
    <div className="mx-auto max-w-5xl px-5 pb-16 pt-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="display flex items-center gap-2 text-2xl font-bold uppercase tracking-wide">
            <SoccerBall className="h-6 w-6" />
            How the ratings are built
          </h2>
          <p className="max-w-xl text-sm text-muted">
            Every team enters at <span className="tabnum text-accent">1500</span> on debut; its Elo
            is nudged after each match — bigger upsets and bigger margins move it more. This rolling
            rating is the strength signal the simulator predicts from.
          </p>
        </div>
        <button
          onClick={reset}
          className="shrink-0 rounded-lg border border-line px-3 py-1.5 text-xs font-semibold uppercase tracking-widest transition hover:border-accent"
        >
          ← Back
        </button>
      </div>

      {error && <div className="text-loss">Couldn't load ratings history ({error}).</div>}
      {!data && !error && <div className="py-24 text-center text-muted">Loading ratings…</div>}

      {chart && (
        <div className="rounded-xl border border-line bg-stage-2/40 p-4">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
            <g transform={`translate(${M.left},${M.top})`}>
              {chart.y.ticks(6).map((t) => (
                <g key={t}>
                  <line
                    x1={0}
                    x2={IW}
                    y1={chart.y(t)}
                    y2={chart.y(t)}
                    stroke="var(--color-line)"
                    opacity={0.5}
                  />
                  <text
                    x={-8}
                    y={chart.y(t)}
                    dy="0.32em"
                    textAnchor="end"
                    fill="var(--color-muted)"
                    fontSize={11}
                    className="tabnum"
                  >
                    {t}
                  </text>
                </g>
              ))}

              <line
                x1={0}
                x2={IW}
                y1={chart.y(1500)}
                y2={chart.y(1500)}
                stroke="var(--color-accent)"
                strokeWidth={1.5}
                strokeDasharray="5 4"
                opacity={0.7}
              />
              <text
                x={4}
                y={chart.y(1500) - 6}
                fill="var(--color-accent)"
                fontSize={11}
                className="tabnum"
              >
                1500 · start
              </text>

              {chart.x.ticks(8).map((d) => (
                <text
                  key={+d}
                  x={chart.x(d)}
                  y={IH + 20}
                  textAnchor="middle"
                  fill="var(--color-muted)"
                  fontSize={11}
                  className="tabnum"
                >
                  {d.getFullYear()}
                </text>
              ))}

              {/* Faint lines first; highlighted teams drawn on top. */}
              {chart.ranked
                .slice()
                .reverse()
                .map((code) => {
                  const isTop = chart.topCodes.includes(code);
                  const delay = isTop ? chart.topCodes.indexOf(code) * 0.12 : 0;
                  return (
                    <path
                      key={code}
                      d={chart.line(chart.parsed[code]) ?? ""}
                      fill="none"
                      stroke={chart.colorOf(code)}
                      strokeWidth={isTop ? 2.2 : 1}
                      pathLength={1}
                      style={{
                        strokeDasharray: "1",
                        strokeDashoffset: drawn ? "0" : "1",
                        // Reset must be instant, otherwise Replay's un-draw and
                        // re-draw transitions cancel each other out.
                        transition: drawn ? `stroke-dashoffset 3s ease ${delay}s` : "none",
                      }}
                    />
                  );
                })}

              {chart.topCodes.map((code) => {
                const yv = chart.y(chart.lastElo(code));
                const iso2 = teams[code]?.iso2;
                return (
                  <g
                    key={code}
                    transform={`translate(${IW + 6},${yv})`}
                    style={{
                      opacity: drawn ? 1 : 0,
                      transition: drawn ? "opacity 0.5s ease 2.6s" : "none",
                    }}
                  >
                    {iso2 && <image href={`https://flagcdn.com/${iso2}.svg`} width={16} height={11} y={-6} />}
                    <text x={22} dy="0.32em" fill={chart.colorOf(code)} fontSize={11} fontWeight={700}>
                      {code}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>

          <div className="mt-3 flex items-center justify-between">
            <span className="text-[11px] text-muted/70">
              Rolling World-Football Elo · {chart.x.domain()[0].getFullYear()}–
              {chart.x.domain()[1].getFullYear()}
            </span>
            <button
              onClick={() => setRunId((r) => r + 1)}
              className="rounded-md border border-line px-3 py-1 text-xs font-semibold uppercase tracking-widest text-muted transition hover:text-ink"
            >
              Replay
            </button>
          </div>
        </div>
      )}

      {model && (
        <div className="mt-4 rounded-xl border border-line bg-panel/50 p-4">
          <div className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted">
            Model fit · Dixon-Coles Poisson
          </div>
          <div className="flex flex-wrap gap-x-8 gap-y-3">
            <Stat label="μ base rate" value={model.mu.toFixed(3)} />
            <Stat label="γ home" value={model.gamma.toFixed(3)} />
            <Stat label="β elo→goals" value={model.beta.toFixed(3)} />
            <Stat label="ρ low-score" value={model.rho.toFixed(3)} />
            {model.metrics && <Stat label="RPS ↓ better" value={String(model.metrics.rps)} accent />}
            <Stat label="matches" value={model.nTrain.toLocaleString()} />
            <Stat label="through" value={model.trainedThrough} />
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-muted/70">{label}</div>
      <div className={`tabnum text-lg font-bold ${accent ? "text-accent" : "text-ink"}`}>{value}</div>
    </div>
  );
}
