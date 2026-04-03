import type { SearchHit, StatsResponse, StoryFull, StoryLight } from "@/types";

const base = () => import.meta.env.VITE_API_BASE || "/api";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export async function fetchStories(tag?: string): Promise<StoryLight[]> {
  const u = new URL(`${base()}/stories`, window.location.origin);
  if (tag) u.searchParams.set("tag", tag);
  const res = await fetch(u.toString());
  return handle<StoryLight[]>(res);
}

export async function fetchStory(id: number): Promise<StoryFull> {
  const res = await fetch(`${base()}/stories/${id}`);
  return handle<StoryFull>(res);
}

export async function fetchStoriesNear(lat: number, lng: number, radiusKm = 2000): Promise<StoryLight[]> {
  const u = new URL(`${base()}/stories/near`, window.location.origin);
  u.searchParams.set("lat", String(lat));
  u.searchParams.set("lng", String(lng));
  u.searchParams.set("radius_km", String(radiusKm));
  const res = await fetch(u.toString());
  return handle<StoryLight[]>(res);
}

export async function fetchStats(): Promise<StatsResponse> {
  const res = await fetch(`${base()}/stats/countries`);
  return handle<StatsResponse>(res);
}

export async function fetchSummary(): Promise<{ total_stories: number; countries: number }> {
  const res = await fetch(`${base()}/stats/summary`);
  return handle(res);
}

export async function searchStories(q: string): Promise<SearchHit[]> {
  const u = new URL(`${base()}/search`, window.location.origin);
  u.searchParams.set("q", q);
  const res = await fetch(u.toString());
  return handle<SearchHit[]>(res);
}
