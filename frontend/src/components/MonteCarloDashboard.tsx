import * as d3 from "d3";
import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import type { ProbRow } from "../api/types";
import { useSim } from "../store/useSim";
import { Flag, TeamName, pct } from "./common";
import { SoccerBall } from "./decor";

const TOP_N = 16;

const METRICS = [
  { key: "pTitle", label: "Title" },
  { key: "pFinal", label: "Final" },
  { key: "pSF", label: "Semi-finals" },
  { key: "pGroupWinner", label: "Group Winner" },
] as const;

type MetricKey = (typeof METRICS)[number]["key"];

const ROW_COLS = "grid grid-cols-[1.75rem_1.75rem_minmax(6rem,12rem)_1fr_3.75rem] items-center gap-3";

export function MonteCarloDashboard() {
  const probs = useSim((s) => s.probabilities);
  const status = useSim((s) => s.status);
  const reset = useSim((s) => s.reset);
  const [metric, setMetric] = useState<MetricKey>("pTitle");

  const metricLabel = METRICS.find((m) => m.key === metric)!.label;
  const rows = [...(probs?.teams ?? [])]
    .sort((a, b) => b[metric] - a[metric])
    .slice(0, TOP_N);
  const max = d3.max(rows, (r: ProbRow) => r[metric]) ?? 1;
  const x = d3.scaleLinear().domain([0, max || 1]).range([0, 100]);
  const progress = probs && probs.runsTotal ? probs.runsDone / probs.runsTotal : 0;

  return (
    <div className="mx-auto max-w-4xl px-5 pb-16 pt-6">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h2 className="display flex items-center gap-2 text-2xl font-bold uppercase tracking-wide">
            <SoccerBall className="h-6 w-6" />
            Monte Carlo
          </h2>
          <p className="text-sm text-muted">Probabilities across many simulated tournaments.</p>
        </div>
        <div className="text-right">
          <div className="tabnum text-3xl font-bold">
            {probs ? probs.runsDone.toLocaleString() : "0"}
            <span className="text-base text-muted">
              {" "}
              / {probs ? probs.runsTotal.toLocaleString() : "—"}
            </span>
          </div>
          <div className="ml-auto mt-1 h-1.5 w-48 overflow-hidden rounded-full bg-panel">
            <motion.div
              className="h-full bg-accent"
              animate={{ width: `${progress * 100}%` }}
              transition={{ ease: "linear", duration: 0.3 }}
            />
          </div>
        </div>
      </div>

      <div className="mb-4 inline-flex rounded-lg border border-line bg-panel p-1">
        {METRICS.map((m) => (
          <button
            key={m.key}
            onClick={() => setMetric(m.key)}
            className={`rounded-md px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition ${
              metric === m.key ? "bg-accent text-stage" : "text-muted hover:text-ink"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="py-24 text-center text-muted">Warming up the simulator…</div>
      ) : (
        <div className="rounded-xl border border-line bg-stage-2/40 p-4">
          <div className={`${ROW_COLS} px-1 pb-2 text-[10px] uppercase tracking-widest text-muted/60`}>
            <span>#</span>
            <span />
            <span>Team</span>
            <span>{metricLabel} chance</span>
            <span className="text-right">%</span>
          </div>

          <div className="space-y-1.5">
            <AnimatePresence>
              {rows.map((r, i) => (
                <motion.div
                  key={r.team}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ layout: { type: "spring", stiffness: 500, damping: 42 } }}
                  className={`${ROW_COLS} rounded-md px-1 py-0.5 ${i === 0 ? "bg-accent/[0.06]" : ""}`}
                >
                  <span
                    className={`tabnum text-center text-xs font-bold ${i === 0 ? "text-accent" : "text-muted"}`}
                  >
                    {i + 1}
                  </span>
                  <Flag code={r.team} className="h-4 w-6" />
                  <span className="truncate text-sm font-semibold">
                    <TeamName code={r.team} />
                  </span>
                  <div className="relative h-6 overflow-hidden rounded-md bg-panel">
                    <motion.div
                      className={`absolute inset-y-0 left-0 rounded-md ${
                        i === 0
                          ? "bg-gradient-to-r from-cyan to-accent shadow-[0_0_16px_-4px_var(--color-accent)]"
                          : "bg-gradient-to-r from-brand/80 to-cyan/70"
                      }`}
                      animate={{ width: `${x(r[metric])}%` }}
                      transition={{ ease: "easeOut", duration: 0.4 }}
                    />
                  </div>
                  <span
                    className={`tabnum text-right text-sm font-bold ${i === 0 ? "text-accent" : "text-ink"}`}
                  >
                    {pct(r[metric])}
                  </span>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {status === "done" && (
        <button
          onClick={reset}
          className="mt-8 rounded-xl border border-line bg-panel px-6 py-3 display text-sm font-bold uppercase tracking-widest transition hover:border-accent"
        >
          Run again
        </button>
      )}
    </div>
  );
}
