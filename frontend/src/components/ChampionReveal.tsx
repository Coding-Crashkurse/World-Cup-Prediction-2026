import confetti from "canvas-confetti";
import gsap from "gsap";
import { useEffect, useRef } from "react";

import { useSim } from "../store/useSim";
import { Flag, TeamName } from "./common";
import { SoccerBall } from "./decor";

export function ChampionReveal() {
  const champion = useSim((s) => s.champion);
  const koMatches = useSim((s) => s.koMatches);
  const reset = useSim((s) => s.reset);
  const ref = useRef<HTMLDivElement>(null);

  const third = koMatches[103];
  const thirdPlace = third?.winner ?? null;
  const fourthPlace = third ? (third.winner === third.home ? third.away : third.home) : null;

  useEffect(() => {
    if (!champion || !ref.current) return;
    const ctx = gsap.context(() => {
      gsap
        .timeline()
        .from(".champ-pre", { opacity: 0, y: 20, duration: 0.5 })
        .from(".champ-flag", { scale: 0, rotate: -18, duration: 0.7, ease: "back.out(1.7)" }, "+=0.05")
        .from(".champ-name", { y: 70, opacity: 0, duration: 0.6, ease: "power3.out" }, "-=0.25")
        .from(".champ-meta", { opacity: 0, y: 20, duration: 0.5 }, "-=0.15");
    }, ref);

    const colors = ["#d7ff2e", "#2563eb", "#ffffff"];
    confetti({ particleCount: 180, spread: 130, origin: { y: 0.5 }, colors });
    const end = Date.now() + 2600;
    let raf = 0;
    const tick = () => {
      confetti({ particleCount: 5, spread: 75, origin: { x: 0, y: 0.65 }, colors, angle: 60 });
      confetti({ particleCount: 5, spread: 75, origin: { x: 1, y: 0.65 }, colors, angle: 120 });
      if (Date.now() < end) raf = requestAnimationFrame(tick);
    };
    tick();
    return () => {
      cancelAnimationFrame(raf);
      ctx.revert();
    };
  }, [champion]);

  if (!champion) return null;

  return (
    <div ref={ref} className="flex min-h-full flex-col items-center justify-center px-6 py-20 text-center">
      <span className="champ-pre display flex items-center gap-3 text-sm font-semibold uppercase tracking-[0.4em] text-accent">
        <SoccerBall className="h-5 w-5" />
        World Champion 2026
        <SoccerBall className="h-5 w-5" />
      </span>
      <div className="champ-flag mt-8">
        <Flag code={champion.team} className="h-40 w-60 rounded-xl shadow-2xl" />
      </div>
      <h1 className="champ-name mt-6 display text-7xl font-black uppercase tracking-tight md:text-8xl">
        <TeamName code={champion.team} />
      </h1>
      <div className="champ-meta mt-8 flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-muted">
        <Podium label="Runner-up" code={champion.runnerUp} />
        {thirdPlace && <Podium label="3rd place" code={thirdPlace} />}
        {fourthPlace && <Podium label="4th place" code={fourthPlace} />}
      </div>
      <button
        onClick={reset}
        className="champ-meta mt-12 rounded-xl border border-line bg-panel px-6 py-3 display text-sm font-bold uppercase tracking-widest transition hover:border-accent"
      >
        Run again
      </button>
    </div>
  );
}

function Podium({ label, code }: { label: string; code: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs uppercase tracking-widest text-muted/70">{label}</span>
      <Flag code={code} className="h-4 w-6" />
      <span className="font-semibold text-ink">
        <TeamName code={code} />
      </span>
    </div>
  );
}
