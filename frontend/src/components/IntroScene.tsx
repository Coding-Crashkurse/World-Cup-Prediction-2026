import { motion } from "motion/react";

import { useSim } from "../store/useSim";
import { SoundToggle } from "./SoundToggle";
import { SoccerBall } from "./decor";

const fmtCount = (v: number) => (v >= 1000 ? `${v / 1000}K` : String(v));

export function IntroScene() {
  const {
    mode,
    setMode,
    seed,
    setSeed,
    speed,
    setSpeed,
    iterations,
    setIterations,
    step,
    setStep,
    start,
    showRatings,
    showPredictor,
    model,
    ready,
    loadError,
  } = useSim();

  return (
    <div className="flex min-h-full items-center justify-center px-6 py-16">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="relative w-full max-w-2xl"
      >
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 16, ease: "linear" }}
          className="pointer-events-none absolute -right-2 -top-8 hidden drop-shadow-2xl md:block"
        >
          <SoccerBall className="h-24 w-24" />
        </motion.div>
        <div className="mb-2 flex items-center gap-3 text-accent">
          <SoccerBall className="h-4 w-4" />
          <span className="display text-sm font-semibold uppercase tracking-[0.35em]">
            Road to the Cup
          </span>
        </div>
        <h1 className="display text-6xl font-black uppercase leading-[0.92] tracking-tight md:text-7xl">
          FIFA World Cup
          <span className="block text-accent">2026 Simulator</span>
        </h1>
        <p className="mt-4 max-w-lg text-muted">
          A statistical Dixon-Coles model simulates all 104 matches — thousands of times.
          Watch one tournament unfold, or converge the title odds live.
        </p>

        <div className="mt-8 grid grid-cols-2 gap-3">
          <ModeCard
            active={mode === "single"}
            title="Single Run"
            sub="One dramatic tournament, match by match."
            onClick={() => setMode("single")}
          />
          <ModeCard
            active={mode === "montecarlo"}
            title="Monte Carlo"
            sub="10,000 runs → live probabilities."
            onClick={() => setMode("montecarlo")}
          />
        </div>

        <p className="mt-3 text-sm text-muted">
          {mode === "single"
            ? "A single run plays out one possible tournament, match by match."
            : "Monte Carlo estimates each team's chances across thousands of simulated tournaments."}
        </p>

        {mode === "single" ? (
          <div className="mt-5 grid grid-cols-[1fr_auto] items-end gap-5">
            <label className="block">
              <span className="flex items-center justify-between text-xs uppercase tracking-widest text-muted">
                <span>Playback speed</span>
                <span className="tabnum text-accent">{speed}×</span>
              </span>
              <input
                type="range"
                min={1}
                max={8}
                step={1}
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="mt-2 w-full accent-[var(--color-accent)]"
              />
              <span className="text-[10px] text-muted/70">
                1× = full broadcast pace · higher = faster
              </span>
            </label>
            <SeedField seed={seed} setSeed={setSeed} />
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            <PresetRow
              label="Iterations"
              value={iterations}
              options={[1000, 10000, 50000, 100000]}
              onPick={setIterations}
              fmt={fmtCount}
            />
            <div className="grid grid-cols-[1fr_auto] items-end gap-5">
              <label className="block">
                <span className="flex items-center gap-2 text-xs uppercase tracking-widest text-muted">
                  <span>Update step</span>
                  <span className="tabnum text-accent">{step}</span>
                </span>
                <input
                  type="range"
                  min={1}
                  max={250}
                  step={1}
                  value={step}
                  onChange={(e) => setStep(Number(e.target.value))}
                  className="mt-2 w-full accent-[var(--color-accent)]"
                />
                <span className="mt-1 block text-[10px] text-muted/70">
                  new frame every N simulations (the staircase) — 1 = every run
                </span>
              </label>
              <SeedField seed={seed} setSeed={setSeed} />
            </div>
          </div>
        )}

        <div className="mt-6 flex items-center gap-3">
          <SoundToggle withLabel />
          <span className="text-[11px] text-muted/70">Audio is off by default — toggle before you start.</span>
        </div>

        <button
          onClick={start}
          disabled={!ready}
          className="mt-4 w-full rounded-xl bg-accent px-6 py-4 display text-lg font-bold uppercase tracking-wider text-stage shadow-[0_0_34px_-10px_var(--color-accent)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
        >
          {!ready
            ? "Connecting…"
            : mode === "single"
              ? "Simulate One Tournament"
              : `Run ${iterations.toLocaleString()} Simulations`}
        </button>

        {loadError && (
          <p className="mt-4 rounded-lg border border-loss/40 bg-loss/10 px-4 py-3 text-sm text-loss">
            Backend unreachable ({loadError}). Start it with{" "}
            <code className="tabnum">uv run wm2026 serve</code> (after{" "}
            <code className="tabnum">download-data</code> + <code className="tabnum">train</code>).
          </p>
        )}

        <p className="mt-6 text-sm text-muted">
          A statistical score model based on historical international matches.
        </p>
        <details className="mt-2 rounded-lg border border-line bg-panel/50 px-4 py-3 text-xs text-muted">
          <summary className="flex cursor-pointer items-center justify-between font-semibold uppercase tracking-widest text-muted/90">
            <span>Model details</span>
            {model?.metrics && <span className="tabnum text-accent">RPS {model.metrics.rps}</span>}
          </summary>
          <div className="mt-3 space-y-1.5 leading-relaxed">
            <p>
              <span className="text-ink">Dixon-Coles Poisson</span> — a football-specific scoring
              model that better captures low scorelines (0-0, 1-0, 1-1).
            </p>
            {model && (
              <p>
                Trained on {model.nTrain.toLocaleString()} international matches through{" "}
                {model.trainedThrough}.
              </p>
            )}
            {model?.metrics && (
              <p>
                Ranked Probability Score{" "}
                <span className="tabnum text-ink">{model.metrics.rps}</span> — lower is better. The
                aim is calibration, not just hit-rate.
              </p>
            )}
            <p className="text-muted/70">
              International football is data-sparse and high-variance — a transparent statistical
              toy, not an oracle.
            </p>
          </div>
        </details>
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1">
          <button
            onClick={showRatings}
            className="text-xs font-semibold uppercase tracking-widest text-muted transition hover:text-accent"
          >
            ↗ See how the Elo ratings are built
          </button>
          <button
            onClick={showPredictor}
            className="text-xs font-semibold uppercase tracking-widest text-muted transition hover:text-accent"
          >
            ↗ Try the match predictor
          </button>
        </div>
      </motion.div>
    </div>
  );
}

function ModeCard({
  active,
  title,
  sub,
  onClick,
}: {
  active: boolean;
  title: string;
  sub: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-xl border p-4 text-left transition ${
        active
          ? "border-accent bg-accent/10"
          : "border-line bg-panel hover:border-brand hover:bg-panel-2"
      }`}
    >
      <div className="display text-lg font-bold uppercase tracking-wide">{title}</div>
      <div className="mt-1 text-xs text-muted">{sub}</div>
    </button>
  );
}

function PresetRow({
  label,
  value,
  options,
  onPick,
  fmt,
  hint,
}: {
  label: string;
  value: number;
  options: number[];
  onPick: (n: number) => void;
  fmt: (n: number) => string;
  hint?: string;
}) {
  return (
    <div>
      <span className="flex items-center gap-2 text-xs uppercase tracking-widest text-muted">
        <span>{label}</span>
        <span className="tabnum text-accent">{fmt(value)}</span>
      </span>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {options.map((o) => (
          <button
            key={o}
            onClick={() => onPick(o)}
            className={`rounded-md px-2.5 py-1.5 tabnum text-xs font-bold transition ${
              value === o ? "bg-accent text-stage" : "border border-line text-muted hover:text-ink"
            }`}
          >
            {fmt(o)}
          </button>
        ))}
      </div>
      {hint && <span className="mt-1 block text-[10px] text-muted/70">{hint}</span>}
    </div>
  );
}

function SeedField({ seed, setSeed }: { seed: string; setSeed: (s: string) => void }) {
  return (
    <label className="block">
      <span className="text-xs uppercase tracking-widest text-muted">Seed</span>
      <input
        value={seed}
        onChange={(e) => setSeed(e.target.value)}
        placeholder="random"
        className="mt-1 w-28 rounded-lg border border-line bg-panel px-3 py-2 tabnum text-ink outline-none focus:border-brand"
      />
    </label>
  );
}
