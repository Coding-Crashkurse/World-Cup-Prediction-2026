import { create } from "zustand";

import { fetchGroups, fetchModel, fetchTeams, openSimSocket } from "../api/client";
import { sound } from "../lib/sound";
import type {
  BracketUpdateEvent,
  MatchResultEvent,
  ModelInfo,
  ProbabilitiesEvent,
  SimEvent,
  Stage,
  TableRow,
  Team,
} from "../api/types";

export type Scene =
  | "intro"
  | "group"
  | "knockout"
  | "champion"
  | "montecarlo"
  | "ratings"
  | "predictor";
export type Mode = "single" | "montecarlo";
export type Status = "idle" | "running" | "done" | "error";

let socket: WebSocket | null = null;

// Detach handlers BEFORE closing: close() is async, so buffered frames would
// otherwise still reach onmessage and mutate state after a reset/restart.
function closeSocket(): void {
  if (socket) {
    socket.onmessage = null;
    socket.onclose = null;
    socket.close();
    socket = null;
  }
}

function zeroRows(codes: string[]): TableRow[] {
  return codes.map((team, i) => ({
    team,
    rank: i + 1,
    p: 0,
    w: 0,
    d: 0,
    l: 0,
    gf: 0,
    ga: 0,
    gd: 0,
    pts: 0,
  }));
}

interface SimState {
  // Static config (loaded once via REST).
  teams: Record<string, Team>;
  groupsConfig: Record<string, string[]>;
  hosts: string[];
  model: ModelInfo | null;
  ready: boolean;
  loadError: string | null;

  // Controls.
  mode: Mode;
  seed: string;
  speed: number;
  iterations: number; // total Monte-Carlo runs
  step: number; // emit a progress frame every `step` runs (the staircase)
  muted: boolean;

  // Live state.
  scene: Scene;
  status: Status;
  errorMsg: string | null;
  currentStage: Stage | null;
  matchday: number;
  groups: Record<string, TableRow[]>;
  lastMatch: MatchResultEvent | null;
  ticker: MatchResultEvent[];
  bracket: Record<number, BracketUpdateEvent>;
  koMatches: Record<number, MatchResultEvent>;
  seeds: Record<number, { home: string; away: string }>; // pairings shown before the result

  thirds: { team: string; group: string; qualified: boolean }[];
  champion: { team: string; runnerUp: string } | null;
  probabilities: ProbabilitiesEvent | null;
  stingerKey: number;

  loadStatic: () => Promise<void>;
  setMode: (m: Mode) => void;
  setSeed: (s: string) => void;
  setSpeed: (s: number) => void;
  setIterations: (n: number) => void;
  setStep: (n: number) => void;
  toggleMuted: () => void;
  showRatings: () => void;
  showPredictor: () => void;
  start: () => void;
  reset: () => void;
}

export const useSim = create<SimState>((set, get) => ({
  teams: {},
  groupsConfig: {},
  hosts: [],
  model: null,
  ready: false,
  loadError: null,

  mode: "single",
  seed: "",
  speed: 1,
  iterations: 10000,
  step: 25,
  muted: true,

  scene: "intro",
  status: "idle",
  errorMsg: null,
  currentStage: null,
  matchday: 0,
  groups: {},
  lastMatch: null,
  ticker: [],
  bracket: {},
  koMatches: {},
  seeds: {},
  thirds: [],
  champion: null,
  probabilities: null,
  stingerKey: 0,

  loadStatic: async () => {
    try {
      const [teamsRes, groupsRes, modelRes] = await Promise.all([
        fetchTeams(),
        fetchGroups(),
        fetchModel().catch(() => null),
      ]);
      const teams: Record<string, Team> = {};
      for (const t of teamsRes.teams) teams[t.code] = t;
      set({
        teams,
        groupsConfig: groupsRes.groups,
        hosts: groupsRes.hosts,
        model: modelRes,
        ready: true,
        loadError: null,
      });
    } catch (e) {
      set({ loadError: (e as Error).message, ready: false });
    }
  },

  setMode: (mode) => set({ mode }),
  setSeed: (seed) => set({ seed }),
  setSpeed: (speed) => set({ speed }),
  setIterations: (iterations) => set({ iterations }),
  setStep: (step) => set({ step }),
  showRatings: () => set({ scene: "ratings" }),
  showPredictor: () => set({ scene: "predictor" }),
  toggleMuted: () => {
    sound.ensure(); // runs inside a user gesture, satisfying autoplay policy
    const muted = !get().muted;
    sound.setMuted(muted);
    set({ muted });
  },

  start: () => {
    const { mode, seed, speed, iterations, step, groupsConfig, muted } = get();
    sound.ensure();
    sound.setMuted(muted);
    closeSocket();

    const initialGroups: Record<string, TableRow[]> = {};
    for (const [g, codes] of Object.entries(groupsConfig)) initialGroups[g] = zeroRows(codes);

    set({
      status: "running",
      errorMsg: null,
      scene: mode === "single" ? "group" : "montecarlo",
      currentStage: mode === "single" ? "group" : null,
      matchday: 0,
      groups: initialGroups,
      lastMatch: null,
      ticker: [],
      bracket: {},
      koMatches: {},
      seeds: {},
      thirds: [],
      champion: null,
      probabilities: null,
    });

    const seedNum = seed.trim() === "" ? null : Number(seed);
    socket = openSimSocket(
      { mode, seed: seedNum, speed, n: iterations, step },
      (ev) => handleEvent(set, get, ev),
      () => {
        if (get().status === "running") set({ status: "done" });
      },
    );
  },

  reset: () => {
    // Only return to the intro; the next start() wipes the run data fresh.
    // (Clearing it here would blank the outgoing scene during its exit anim.)
    closeSocket();
    set({ scene: "intro", status: "idle" });
  },
}));

function handleEvent(
  set: (partial: Partial<SimState>) => void,
  get: () => SimState,
  ev: SimEvent,
): void {
  switch (ev.type) {
    case "match_result": {
      const ticker = [ev, ...get().ticker].slice(0, 8);
      const patch: Partial<SimState> = { lastMatch: ev, ticker };
      if (ev.matchNo != null) patch.koMatches = { ...get().koMatches, [ev.matchNo]: ev };
      set(patch);
      sound.kick();
      break;
    }
    case "table_update":
      set({ groups: { ...get().groups, [ev.group]: ev.rows } });
      break;
    case "matchday":
      set({ matchday: ev.matchday });
      break;
    case "stage_change":
      set({ currentStage: ev.to });
      if (ev.to === "R32") set({ scene: "knockout", stingerKey: get().stingerKey + 1 });
      sound.whoosh();
      break;
    case "bracket_seed":
      set({ seeds: { ...get().seeds, [ev.matchNo]: { home: ev.home, away: ev.away } } });
      break;
    case "bracket_update":
      set({ bracket: { ...get().bracket, [ev.matchNo]: ev } });
      break;
    case "third_place_ranking":
      set({ thirds: ev.ranked });
      break;
    case "probabilities":
      set({ probabilities: ev });
      sound.tick(ev.runsTotal ? ev.runsDone / ev.runsTotal : 0);
      break;
    case "champion":
      set({ champion: { team: ev.team, runnerUp: ev.runnerUp }, scene: "champion" });
      sound.cheer();
      break;
    case "done":
      set({ status: "done" });
      if (get().mode === "montecarlo") sound.fanfare();
      break;
    case "error":
      set({ status: "error", errorMsg: ev.message });
      break;
  }
}
