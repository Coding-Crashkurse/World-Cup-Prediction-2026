import * as d3 from "d3";
import gsap from "gsap";
import { motion } from "motion/react";
import { useEffect, useMemo, useRef } from "react";

import type { MatchResultEvent, Stage } from "../api/types";
import { useSim } from "../store/useSim";
import { Flag } from "./common";

// Leaf order so each match at index i (round r) is fed by 2i and 2i+1 (round r-1).
const ROUNDS: { key: Stage; label: string; matches: number[] }[] = [
  { key: "R32", label: "Round of 32", matches: [74, 77, 73, 75, 83, 84, 81, 82, 76, 78, 79, 80, 86, 88, 85, 87] },
  { key: "R16", label: "Round of 16", matches: [89, 90, 93, 94, 91, 92, 95, 96] },
  { key: "QF", label: "Quarter-finals", matches: [97, 98, 99, 100] },
  { key: "SF", label: "Semi-finals", matches: [101, 102] },
  { key: "F", label: "Final", matches: [104] },
];

const CARD_W = 156;
const CARD_H = 48;
const COL_GAP = 58;
const ROW_GAP = 12;
const LEAF = CARD_H + ROW_GAP;

function MatchCard({
  match,
  seed,
  big = false,
}: {
  match?: MatchResultEvent;
  seed?: { home: string; away: string };
  big?: boolean;
}) {
  // Teams come from the result once played, otherwise from the early seeding.
  const home = match?.home ?? seed?.home ?? null;
  const away = match?.away ?? seed?.away ?? null;
  const rows = [
    { code: home, goals: match ? match.score[0] : null, win: match ? match.winner === home : false },
    { code: away, goals: match ? match.score[1] : null, win: match ? match.winner === away : false },
  ];
  const decided =
    match?.decidedBy === "penalties"
      ? `p ${match.pens?.[0]}-${match.pens?.[1]}`
      : match?.decidedBy === "extra_time"
        ? "aet"
        : "";

  return (
    <motion.div
      initial={match || seed ? { opacity: 0, scale: 0.9 } : false}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, ease: "backOut" }}
      className={`flex h-full flex-col justify-center overflow-hidden rounded-lg border ${
        big ? "border-accent bg-accent/10" : "border-line bg-panel"
      }`}
    >
      {rows.map((r, i) => (
        <div
          key={i}
          className={`flex items-center gap-2 px-2 py-1 ${i === 0 ? "border-b border-line/60" : ""} ${
            r.win ? "bg-win/10" : ""
          }`}
        >
          {r.code ? <Flag code={r.code} className="h-3 w-[18px]" /> : <span className="h-3 w-[18px]" />}
          <span
            className={`flex-1 truncate text-xs font-semibold ${
              r.win ? "text-win" : !r.code ? "text-muted/40" : match ? "text-ink" : "text-muted"
            }`}
          >
            {r.code ?? "—"}
          </span>
          {decided && i === 1 && <span className="tabnum text-[8px] text-muted">{decided}</span>}
          <span className={`tabnum w-4 text-right text-xs ${r.win ? "font-bold text-win" : "text-muted"}`}>
            {r.goals ?? ""}
          </span>
        </div>
      ))}
    </motion.div>
  );
}

function Bracket() {
  const koMatches = useSim((s) => s.koMatches);
  const seeds = useSim((s) => s.seeds);

  const positions = useMemo(() => {
    const pos: Record<number, { x: number; y: number }> = {};
    ROUNDS.forEach((round, r) => {
      round.matches.forEach((m, i) => {
        const x = r * (CARD_W + COL_GAP);
        let y: number;
        if (r === 0) {
          y = i * LEAF;
        } else {
          const prev = ROUNDS[r - 1].matches;
          y = (pos[prev[2 * i]].y + pos[prev[2 * i + 1]].y) / 2;
        }
        pos[m] = { x, y };
      });
    });
    return pos;
  }, []);

  const width = ROUNDS.length * (CARD_W + COL_GAP) - COL_GAP;
  const height = ROUNDS[0].matches.length * LEAF - ROW_GAP;

  const link = d3.linkHorizontal();
  const connectors = useMemo(() => {
    const out: { d: string; lit: boolean }[] = [];
    for (let r = 1; r < ROUNDS.length; r++) {
      const prev = ROUNDS[r - 1].matches;
      ROUNDS[r].matches.forEach((m, i) => {
        const parent = positions[m];
        const lit = !!(koMatches[m] || seeds[m]);
        for (const child of [prev[2 * i], prev[2 * i + 1]]) {
          const c = positions[child];
          const d = link({
            source: [c.x + CARD_W, c.y + CARD_H / 2],
            target: [parent.x, parent.y + CARD_H / 2],
          });
          if (d) out.push({ d, lit });
        }
      });
    }
    return out;
  }, [positions, koMatches, seeds, link]);

  return (
    <div className="relative" style={{ width, height }}>
      <svg className="absolute inset-0" width={width} height={height}>
        {connectors.map((c, i) => (
          <path
            key={i}
            d={c.d}
            fill="none"
            stroke={c.lit ? "var(--color-brand)" : "var(--color-line)"}
            strokeWidth={c.lit ? 2 : 1}
            opacity={c.lit ? 0.9 : 0.5}
          />
        ))}
      </svg>
      {ROUNDS.map((round) =>
        round.matches.map((m) => (
          <div
            key={m}
            className="absolute"
            style={{ left: positions[m].x, top: positions[m].y, width: CARD_W, height: CARD_H }}
          >
            <MatchCard match={koMatches[m]} seed={seeds[m]} big={m === 104} />
          </div>
        )),
      )}
    </div>
  );
}

function Stinger({ trigger }: { trigger: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const tl = gsap.timeline();
    tl.set(el, { autoAlpha: 1 })
      .fromTo(
        el.querySelector(".stinger-bar"),
        { scaleX: 0, transformOrigin: "left" },
        { scaleX: 1, duration: 0.4, ease: "power3.inOut" },
      )
      .fromTo(
        el.querySelector(".stinger-text"),
        { y: 40, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.4, ease: "power2.out" },
        "-=0.1",
      )
      .to(el.querySelector(".stinger-text"), { opacity: 1, duration: 0.6 })
      .to(el, { autoAlpha: 0, duration: 0.4 });
    return () => {
      tl.kill();
    };
  }, [trigger]);

  return (
    <div
      ref={ref}
      className="pointer-events-none fixed inset-0 z-40 flex items-center justify-center"
      style={{ visibility: "hidden" }}
    >
      <div className="stinger-bar absolute inset-x-0 top-1/2 h-24 -translate-y-1/2 bg-brand/90" />
      <h2 className="stinger-text display relative text-6xl font-black uppercase tracking-[0.2em] text-stage md:text-8xl">
        Knockout
      </h2>
    </div>
  );
}

export function KnockoutScene() {
  const stingerKey = useSim((s) => s.stingerKey);
  const koMatches = useSim((s) => s.koMatches);
  const seeds = useSim((s) => s.seeds);
  const thirdPlace = koMatches[103];
  const thirdSeed = seeds[103];

  return (
    <div className="mx-auto max-w-[1200px] px-5 pb-16 pt-6">
      <Stinger trigger={stingerKey} />
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6, duration: 0.5 }}
      >
        <div className="mb-4 flex items-end justify-between">
          <h2 className="display text-2xl font-bold uppercase tracking-wide">Knockout Bracket</h2>
          <div className="hidden gap-6 md:flex">
            {ROUNDS.map((r) => (
              <span key={r.key} className="text-[11px] uppercase tracking-widest text-muted">
                {r.label}
              </span>
            ))}
          </div>
        </div>

        <div className="overflow-auto rounded-xl border border-line bg-stage-2/40 p-5">
          <Bracket />
        </div>

        {(thirdPlace || thirdSeed) && (
          <div className="mt-4 flex items-center gap-3">
            <span className="text-[11px] uppercase tracking-widest text-muted">3rd-place play-off</span>
            <div className="w-40">
              <MatchCard match={thirdPlace} seed={thirdSeed} />
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
