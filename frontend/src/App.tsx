import { AnimatePresence, motion } from "motion/react";
import { useEffect } from "react";

import { ChampionReveal } from "./components/ChampionReveal";
import { EloHistory } from "./components/EloHistory";
import { GroupStage } from "./components/GroupStage";
import { IntroScene } from "./components/IntroScene";
import { KnockoutScene } from "./components/KnockoutBracket";
import { MonteCarloDashboard } from "./components/MonteCarloDashboard";
import { Predictor } from "./components/Predictor";
import { STAGE_LABEL } from "./components/common";
import { PitchLines, SoccerBall } from "./components/decor";
import { SoundToggle } from "./components/SoundToggle";
import { useSim } from "./store/useSim";

function TopBar() {
  const { scene, status, currentStage, mode, reset } = useSim();
  if (scene === "intro" || scene === "ratings" || scene === "predictor") return null;
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-stage/80 px-5 py-3 backdrop-blur">
      <div className="flex items-center gap-3">
        <SoccerBall className="h-5 w-5" />
        <span className="display text-sm font-bold uppercase tracking-[0.3em]">Road to the Cup</span>
        <span className="hidden text-xs uppercase tracking-widest text-muted sm:inline">
          {mode === "single" ? "Single Run" : "Monte Carlo"}
        </span>
      </div>
      <div className="flex items-center gap-4">
        {currentStage && scene !== "champion" && (
          <span className="hidden text-xs uppercase tracking-widest text-muted md:inline">
            {STAGE_LABEL[currentStage]}
          </span>
        )}
        <span
          className={`flex items-center gap-1.5 text-xs uppercase tracking-widest ${
            status === "running" ? "text-accent" : "text-muted"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${status === "running" ? "animate-pulse bg-accent" : "bg-muted"}`}
          />
          {status}
        </span>
        <SoundToggle />
        <button
          onClick={reset}
          className="rounded-lg border border-line px-3 py-1.5 text-xs font-semibold uppercase tracking-widest transition hover:border-accent"
        >
          Reset
        </button>
      </div>
    </header>
  );
}

function Scene() {
  const scene = useSim((s) => s.scene);
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={scene}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.4 }}
      >
        {scene === "intro" && <IntroScene />}
        {scene === "ratings" && <EloHistory />}
        {scene === "predictor" && <Predictor />}
        {scene === "group" && <GroupStage />}
        {scene === "knockout" && <KnockoutScene />}
        {scene === "champion" && <ChampionReveal />}
        {scene === "montecarlo" && <MonteCarloDashboard />}
      </motion.div>
    </AnimatePresence>
  );
}

export default function App() {
  const loadStatic = useSim((s) => s.loadStatic);
  useEffect(() => {
    loadStatic();
  }, [loadStatic]);

  return (
    <div className="stage-bg relative min-h-full">
      <PitchLines className="pointer-events-none fixed inset-0 h-full w-full text-pitch opacity-[0.09]" />
      <TopBar />
      <Scene />
    </div>
  );
}
