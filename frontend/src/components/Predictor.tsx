import { useEffect, useMemo, useState } from "react";

import { fetchPredict } from "../api/client";
import type { PredictResponse } from "../api/types";
import { useSim } from "../store/useSim";
import { Flag, TeamName, pct } from "./common";
import { SoccerBall } from "./decor";

export function Predictor() {
  const teams = useSim((s) => s.teams);
  const reset = useSim((s) => s.reset);
  const [home, setHome] = useState("ESP");
  const [away, setAway] = useState("ARG");
  const [neutral, setNeutral] = useState(true);
  const [data, setData] = useState<PredictResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const options = useMemo(
    () => Object.values(teams).sort((a, b) => a.name.localeCompare(b.name)),
    [teams],
  );

  useEffect(() => {
    let alive = true;
    fetchPredict(home, away, neutral)
      .then((d) => alive && (setData(d), setErr(null)))
      .catch((e) => alive && setErr((e as Error).message));
    return () => {
      alive = false;
    };
  }, [home, away, neutral]);

  const maxP = data ? Math.max(...data.grid.flat()) : 1;
  const topCell = data?.top[0];

  return (
    <div className="mx-auto max-w-4xl px-5 pb-16 pt-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="display flex items-center gap-2 text-2xl font-bold uppercase tracking-wide">
            <SoccerBall className="h-6 w-6" />
            Match predictor
          </h2>
          <p className="max-w-xl text-sm text-muted">
            The model turns the Elo gap into expected goals, then a Dixon-Coles Poisson grid of every
            scoreline. Brighter cell = more likely. This is exactly what the simulator samples from.
          </p>
        </div>
        <button
          onClick={reset}
          className="shrink-0 rounded-lg border border-line px-3 py-1.5 text-xs font-semibold uppercase tracking-widest transition hover:border-accent"
        >
          ← Back
        </button>
      </div>

      <div className="mb-5 flex flex-wrap items-end gap-3">
        <Picker label="Home" code={home} options={options} onChange={setHome} />
        <button
          onClick={() => {
            setHome(away);
            setAway(home);
          }}
          title="Swap"
          className="mb-1 rounded-lg border border-line px-3 py-2 text-muted transition hover:text-accent"
        >
          ↔
        </button>
        <Picker label="Away" code={away} options={options} onChange={setAway} />
        <button
          onClick={() => setNeutral((v) => !v)}
          className={`mb-1 rounded-lg border px-3 py-2 text-xs font-semibold uppercase tracking-widest transition ${
            neutral ? "border-line text-muted" : "border-accent bg-accent/10 text-accent"
          }`}
        >
          {neutral ? "Neutral venue" : `${home} at home`}
        </button>
      </div>

      {err && <div className="text-loss">Couldn't predict ({err}).</div>}

      {data && (
        <div className="grid gap-6 md:grid-cols-[auto_1fr]">
          <div>
            <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-widest text-muted">
              <span>away goals →</span>
            </div>
            <Heatmap data={data} maxP={maxP} topCell={topCell} />
            <div className="mt-1 text-xs uppercase tracking-widest text-muted">↓ home goals</div>
          </div>

          <div>
            <div className="flex items-center gap-3 text-lg font-bold">
              <Flag code={data.home} className="h-5 w-7" />
              <TeamName code={data.home} />
              <span className="tabnum text-accent">{data.lambdaHome.toFixed(2)}</span>
              <span className="text-muted">–</span>
              <span className="tabnum text-accent">{data.lambdaAway.toFixed(2)}</span>
              <TeamName code={data.away} />
              <Flag code={data.away} className="h-5 w-7" />
            </div>
            <div className="text-xs text-muted">expected goals (λ)</div>

            <div className="mt-4">
              <div className="mb-1 flex justify-between text-xs uppercase tracking-widest text-muted">
                <span>{data.home} win {pct(data.pHome)}</span>
                <span>draw {pct(data.pDraw)}</span>
                <span>{data.away} win {pct(data.pAway)}</span>
              </div>
              <div className="flex h-3 overflow-hidden rounded-full">
                <div style={{ width: `${data.pHome * 100}%` }} className="bg-brand" />
                <div style={{ width: `${data.pDraw * 100}%` }} className="bg-muted/50" />
                <div style={{ width: `${data.pAway * 100}%` }} className="bg-[#fb7185]" />
              </div>
            </div>

            <div className="mt-5">
              <div className="mb-2 text-xs uppercase tracking-widest text-muted">
                Most likely scorelines
              </div>
              <div className="space-y-1.5">
                {data.top.map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className={`tabnum w-12 font-bold ${i === 0 ? "text-accent" : ""}`}>
                      {s.home}–{s.away}
                    </span>
                    <div className="h-2 flex-1 overflow-hidden rounded bg-panel">
                      <div
                        className={i === 0 ? "h-full bg-accent" : "h-full bg-brand/70"}
                        style={{ width: `${(s.p / maxP) * 100}%` }}
                      />
                    </div>
                    <span className="tabnum w-12 text-right text-muted">{pct(s.p)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Picker({
  label,
  code,
  options,
  onChange,
}: {
  label: string;
  code: string;
  options: { code: string; name: string }[];
  onChange: (c: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] uppercase tracking-widest text-muted">{label}</span>
      <div className="flex items-center gap-2 rounded-lg border border-line bg-panel px-2 py-1.5">
        <Flag code={code} className="h-4 w-6" />
        <select
          value={code}
          onChange={(e) => onChange(e.target.value)}
          className="bg-transparent text-sm font-semibold text-ink outline-none"
        >
          {options.map((t) => (
            <option key={t.code} value={t.code} className="bg-stage-2 text-ink">
              {t.name}
            </option>
          ))}
        </select>
      </div>
    </label>
  );
}

function Heatmap({
  data,
  maxP,
  topCell,
}: {
  data: PredictResponse;
  maxP: number;
  topCell?: { home: number; away: number };
}) {
  const n = data.maxGoals + 1;
  return (
    <div
      className="grid gap-[2px]"
      style={{ gridTemplateColumns: `1.4rem repeat(${n}, 2.3rem)` }}
    >
      <div />
      {Array.from({ length: n }, (_, y) => (
        <div key={`h${y}`} className="tabnum text-center text-[11px] text-muted">
          {y}
        </div>
      ))}
      {data.grid.map((rowArr, x) => (
        <Row
          key={x}
          x={x}
          row={rowArr}
          maxP={maxP}
          topCell={topCell}
        />
      ))}
    </div>
  );
}

function Row({
  x,
  row,
  maxP,
  topCell,
}: {
  x: number;
  row: number[];
  maxP: number;
  topCell?: { home: number; away: number };
}) {
  return (
    <>
      <div className="tabnum flex items-center justify-center text-[11px] text-muted">{x}</div>
      {row.map((p, y) => {
        const alpha = maxP > 0 ? p / maxP : 0;
        const isTop = topCell && x === topCell.home && y === topCell.away;
        const isDraw = x === y;
        return (
          <div
            key={y}
            className={`flex aspect-square items-center justify-center rounded-[3px] text-[10px] tabnum ${
              isTop ? "ring-2 ring-accent" : isDraw ? "ring-1 ring-line" : ""
            }`}
            style={{
              background: `rgba(200,255,53,${alpha.toFixed(3)})`,
              color: alpha > 0.45 ? "var(--color-stage)" : "var(--color-muted)",
            }}
          >
            {p >= 0.012 ? Math.round(p * 100) : ""}
          </div>
        );
      })}
    </>
  );
}
