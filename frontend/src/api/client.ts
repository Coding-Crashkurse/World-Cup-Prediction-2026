import type { EloHistory, ModelInfo, PredictResponse, SimEvent, Team } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export function fetchTeams(): Promise<{ teams: Team[] }> {
  return getJson("/teams");
}

export function fetchGroups(): Promise<{
  groups: Record<string, string[]>;
  hosts: string[];
  bracket: { r32: unknown[]; knockout: unknown[] };
}> {
  return getJson("/groups");
}

export function fetchModel(): Promise<ModelInfo> {
  return getJson("/model");
}

export function fetchEloHistory(): Promise<EloHistory> {
  return getJson("/elo-history");
}

export function fetchPredict(
  home: string,
  away: string,
  neutral: boolean,
): Promise<PredictResponse> {
  const q = new URLSearchParams({ home, away, neutral: String(neutral) });
  return getJson(`/predict?${q.toString()}`);
}

export interface SimParams {
  mode: "single" | "montecarlo";
  n?: number;
  seed?: number | null;
  speed?: number;
  step?: number;
}

export function openSimSocket(
  params: SimParams,
  onEvent: (ev: SimEvent) => void,
  onClose?: () => void,
): WebSocket {
  const wsBase = API_BASE.replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/ws/simulate`);
  ws.onopen = () => ws.send(JSON.stringify(params));
  ws.onmessage = (e) => onEvent(JSON.parse(e.data) as SimEvent);
  if (onClose) ws.onclose = onClose;
  return ws;
}
