import { useMemo, useState } from "react";
import type { CountryGroup, Lang, StoryLight } from "@/types";
import { formatCountryForDisplay } from "@/utils/countryDisplay";

type Props = {
  groups: CountryGroup[];
  lang: Lang;
  selectedCountry: string | null;
  onSelectCountry: (c: string | null) => void;
  onPickStory: (id: number) => void;
  maxCount: number;
};

export function CountrySidebar({
  groups,
  lang,
  selectedCountry,
  onSelectCountry,
  onPickStory,
  maxCount,
}: Props) {
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return groups;
    return groups.filter((g) => g.country.toLowerCase().includes(s));
  }, [groups, q]);

  return (
    <aside className="glass-panel flex h-full max-h-[min(100vh-8rem,640px)] w-[min(92vw,320px)] flex-col overflow-hidden md:max-h-[min(100vh-6rem,720px)] md:w-[340px]">
      <div className="border-b border-slate-700/50 px-3 py-3 md:px-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-slate-100">Countries</h2>
          <span className="text-slate-500" aria-hidden>
            🔍
          </span>
        </div>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search country..."
          className="w-full rounded-xl border border-slate-700/80 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-500/60 focus:outline-none focus:ring-1 focus:ring-sky-500/40"
        />
      </div>
      <div className="flex-1 overflow-y-auto px-2 py-2 md:px-3">
        {filtered.map((g) => {
          const active = selectedCountry === g.country;
          const ratio = maxCount > 0 ? g.count / maxCount : 0;
          return (
            <button
              key={g.country}
              type="button"
              onClick={() => onSelectCountry(active ? null : g.country)}
              className={`mb-2 w-full rounded-xl px-2 py-2 text-left transition ${
                active ? "bg-sky-950/50 ring-1 ring-sky-500/40" : "hover:bg-slate-900/50"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-100">
                  {formatCountryForDisplay(g.country)}
                </span>
                <span className="text-xs tabular-nums text-sky-300/90">{g.count}</span>
              </div>
              <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800/80">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-sky-600/80 to-cyan-400/70"
                  style={{ width: `${Math.max(6, ratio * 100)}%` }}
                />
              </div>
              {active ? (
                <div className="mt-2 space-y-1 border-t border-slate-700/40 pt-2">
                  {g.stories.slice(0, 6).map((s: StoryLight) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onPickStory(s.id);
                      }}
                      className="flex w-full items-center gap-2 rounded-lg px-1 py-1 text-left text-xs text-slate-300 hover:bg-slate-900/80"
                    >
                      <span className="text-lg">{s.emoji}</span>
                      <span className="truncate">{lang === "zh" ? s.title_zh : s.title_en}</span>
                    </button>
                  ))}
                </div>
              ) : null}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
