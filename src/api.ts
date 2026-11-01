import { invoke } from "@tauri-apps/api/core";

export type Corner = "bottom-right" | "bottom-left" | "top-right" | "top-left";

export interface Config {
  name: string;
  character: string;
  interval_min: number;
  snooze_min: number;
  autostart: boolean;
  corner: Corner;
}

export interface Status {
  seconds_left: number;
  waiting_for_answer: boolean;
}

export type Mood = "idle" | "wave" | "happy" | "sad";

export interface CharacterMeta {
  id: string;
  name: string;
  tagline?: string;
  /** Optional per-character greeting; {name} is replaced with the user's name. */
  greeting?: string;
  /** Which moods have a GIF. Missing moods fall back to idle. */
  moods: Mood[];
}

export const getConfig = () => invoke<Config>("get_config");
export const saveConfig = (config: Config) => invoke<void>("save_config", { config });
export const getStatus = () => invoke<Status>("get_status");
export const remindNow = () => invoke<void>("remind_now");
export const answerDone = () => invoke<void>("answer_done");
export const answerLater = () => invoke<void>("answer_later");

let cache: CharacterMeta[] | null = null;

/** Characters are static files under public/characters/, listed by index.json. */
export async function listCharacters(): Promise<CharacterMeta[]> {
  if (cache) return cache;
  const res = await fetch("/characters/index.json", { cache: "no-store" });
  cache = (await res.json()) as CharacterMeta[];
  return cache;
}

export function gifUrl(meta: CharacterMeta | undefined, mood: Mood, bust = false): string {
  const id = meta?.id ?? "droplet";
  const actual = meta && meta.moods.includes(mood) ? mood : "idle";
  return `/characters/${id}/${actual}.gif${bust ? `?t=${Date.now()}` : ""}`;
}

export function greetingFor(meta: CharacterMeta | undefined, userName: string): string {
  const who = userName.trim() || "there";
  const tpl = meta?.greeting ?? "Hey {name}! 💧 Time for a water break?";
  return tpl.replaceAll("{name}", who);
}
