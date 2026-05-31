import { AnimatePresence, motion } from "motion/react";

import type { MatchResultEvent, TableRow } from "../api/types";
import { useSim } from "../store/useSim";
import { Flag, TeamName } from "./common";
import { SoccerBall } from "./decor";

function LiveTable({ rows }: { rows: TableRow[] }) {
  return (
    <div className="space-y-[3px]">
      {rows.map((r) => (
        <motion.div
          key={r.team}
          layout
          transition={{ type: "spring", stiffness: 550, damping: 38 }}
          className={`flex items-center gap-2 rounded-md px-2 py-[5px] ${
            r.rank <= 2
              ? "bg-win/10"
              : r.rank === 3
                ? "bg-accent/10"
                : "bg-white/[0.015]"
          }`}
        >
          <span
            className={`w-3 text-center text-[11px] font-bold ${
              r.rank <= 2 ? "text-win" : r.rank === 3 ? "text-accent" : "text-muted"
            }`}
          >
            {r.rank}
          </span>
          <Flag code={r.team} className="h-3.5 w-5" />
          <span className="flex-1 truncate text-sm font-semibold">{r.team}</span>
          <span className="tabnum w-5 text-right text-[11px] text-muted">{r.p}</span>
          <span className="tabnum w-7 text-right text-[11px] text-muted">
            {r.gd >= 0 ? `+${r.gd}` : r.gd}
          </span>
          <span className="tabnum w-5 text-right text-sm font-bold">{r.pts}</span>
        </motion.div>
      ))}
    </div>
  );
}

function GroupCard({ group, rows }: { group: string; rows: TableRow[] }) {
  return (
    <div className="rounded-xl border border-line bg-panel/70 p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="display text-sm font-bold uppercase tracking-widest text-muted">
          Group {group}
        </span>
        <span className="tabnum text-[10px] uppercase tracking-wider text-muted/60">P GD PTS</span>
      </div>
      <LiveTable rows={rows} />
    </div>
  );
}

function LowerThird({ match }: { match: MatchResultEvent }) {
  const label = match.group ? `Group ${match.group}` : "Match";
  const homeWin = match.score[0] > match.score[1];
  const awayWin = match.score[1] > match.score[0];
  return (
    <motion.div
      key={`${match.home}-${match.away}-${match.score.join("")}`}
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="pointer-events-none flex items-stretch overflow-hidden rounded-xl border border-line bg-stage-2/95 shadow-2xl backdrop-blur"
    >
      <div className="flex items-center bg-brand px-3 text-[10px] font-bold uppercase tracking-widest text-white">
        {label}
      </div>
      <div className="flex flex-1 items-center gap-3 px-4 py-2">
        <Flag code={match.home} className="h-5 w-7" />
        <span className={`flex-1 text-right font-semibold ${homeWin ? "text-ink" : "text-muted"}`}>
          <TeamName code={match.home} />
        </span>
        <span className="tabnum rounded-md bg-black/40 px-3 py-1 text-xl font-bold">
          {match.score[0]}–{match.score[1]}
        </span>
        <span className={`flex-1 font-semibold ${awayWin ? "text-ink" : "text-muted"}`}>
          <TeamName code={match.away} />
        </span>
        <Flag code={match.away} className="h-5 w-7" />
      </div>
      <div className="flex items-center px-3 tabnum text-[10px] text-muted">
        xG {match.xg[0].toFixed(1)}–{match.xg[1].toFixed(1)}
      </div>
    </motion.div>
  );
}

export function GroupStage() {
  const groups = useSim((s) => s.groups);
  const matchday = useSim((s) => s.matchday);
  const lastMatch = useSim((s) => s.lastMatch);
  const ticker = useSim((s) => s.ticker);
  const letters = Object.keys(groups).sort();

  return (
    <div className="mx-auto max-w-7xl px-5 pb-28 pt-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="display flex items-center gap-2 text-2xl font-bold uppercase tracking-wide">
          <SoccerBall className="h-6 w-6" />
          Group Stage
        </h2>
        <div className="flex items-center gap-2">
          <span className="mr-1 text-xs uppercase tracking-widest text-muted">Matchday</span>
          {[1, 2, 3].map((d) => (
            <span
              key={d}
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                d === matchday
                  ? "bg-accent text-stage"
                  : d < matchday
                    ? "bg-brand/40 text-ink"
                    : "bg-panel text-muted"
              }`}
            >
              {d}
            </span>
          ))}
        </div>
      </div>

      {ticker.length > 0 && (
        <div className="mb-5 flex items-center gap-2 overflow-hidden">
          <span className="shrink-0 text-[10px] uppercase tracking-widest text-muted">Recent</span>
          <AnimatePresence initial={false}>
            {ticker.map((m, i) => (
              <motion.div
                key={m.matchNo ?? `${m.group}-${m.home}-${m.away}`}
                layout
                initial={{ opacity: 0, scale: 0.85, x: -12 }}
                animate={{ opacity: Math.max(0.3, 1 - i * 0.13), scale: 1, x: 0 }}
                exit={{ opacity: 0 }}
                className="flex shrink-0 items-center gap-1.5 rounded-md border border-line bg-panel/70 px-2 py-1"
              >
                <Flag code={m.home} className="h-2.5 w-4" />
                <span className="tabnum text-xs font-bold">
                  {m.score[0]}–{m.score[1]}
                </span>
                <Flag code={m.away} className="h-2.5 w-4" />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
        {letters.map((g) => (
          <GroupCard key={g} group={g} rows={groups[g]} />
        ))}
      </div>

      <div className="fixed inset-x-0 bottom-0 z-20 mx-auto max-w-4xl px-5 pb-5">
        <AnimatePresence mode="wait">{lastMatch && <LowerThird match={lastMatch} />}</AnimatePresence>
      </div>
    </div>
  );
}
