export interface Team {
  code: string;
  name: string;
  iso2: string;
  confederation: string;
  isHost: boolean;
  elo: number;
  flagUrl: string;
}

export interface TableRow {
  team: string;
  rank: number;
  p: number;
  w: number;
  d: number;
  l: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
}

export interface ModelInfo {
  mu: number;
  gamma: number;
  beta: number;
  rho: number;
  trainedThrough: string;
  nTrain: number;
  halfLifeYears: number;
  metrics: { rps: number; log_loss: number; accuracy: number } | null;
}

export interface PredictResponse {
  home: string;
  away: string;
  neutral: boolean;
  lambdaHome: number;
  lambdaAway: number;
  pHome: number;
  pDraw: number;
  pAway: number;
  maxGoals: number;
  grid: number[][]; // grid[homeGoals][awayGoals] = probability
  top: { home: number; away: number; p: number }[];
}

export interface EloHistory {
  baseline: number;
  windowStart?: string;
  series: Record<string, [string, number][]>; // team code -> [isoDate, elo][]
}

export interface ProbRow {
  team: string;
  pGroupWinner: number;
  pGroupSecond: number;
  pR32: number;
  pR16: number;
  pQF: number;
  pSF: number;
  pFinal: number;
  pTitle: number;
}

export type Stage = "group" | "R32" | "R16" | "QF" | "SF" | "3P" | "F";

export interface MatchResultEvent {
  type: "match_result";
  stage: Stage;
  group: string | null;
  matchNo: number | null;
  home: string;
  away: string;
  score: [number, number];
  xg: [number, number];
  neutral: boolean;
  decidedBy: "regulation" | "extra_time" | "penalties";
  winner: string | null;
  pens: [number, number] | null;
}

export interface TableUpdateEvent {
  type: "table_update";
  group: string;
  rows: TableRow[];
}

export interface StageChangeEvent {
  type: "stage_change";
  from: Stage | null;
  to: Stage;
}

export interface MatchdayEvent {
  type: "matchday";
  stage: Stage;
  matchday: number;
}

export interface BracketUpdateEvent {
  type: "bracket_update";
  matchNo: number;
  round: Stage;
  home: string;
  away: string;
  winner: string | null;
}

export interface BracketSeedEvent {
  type: "bracket_seed";
  matchNo: number;
  round: Stage;
  home: string;
  away: string;
}

export interface ThirdRankingEvent {
  type: "third_place_ranking";
  ranked: { team: string; group: string; qualified: boolean }[];
}

export interface ProbabilitiesEvent {
  type: "probabilities";
  runsDone: number;
  runsTotal: number;
  teams: ProbRow[];
}

export interface ChampionEvent {
  type: "champion";
  team: string;
  runnerUp: string;
}

export interface DoneEvent {
  type: "done";
  mode: "single" | "montecarlo";
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export type SimEvent =
  | MatchResultEvent
  | TableUpdateEvent
  | StageChangeEvent
  | MatchdayEvent
  | BracketUpdateEvent
  | BracketSeedEvent
  | ThirdRankingEvent
  | ProbabilitiesEvent
  | ChampionEvent
  | DoneEvent
  | ErrorEvent;
