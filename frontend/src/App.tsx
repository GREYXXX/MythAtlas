import { useCallback, useEffect, useMemo, useState } from "react";
import { CountrySidebar } from "@/components/CountrySidebar";
import { FilterBar, eraTagQuery, type ThemeKey, type EraKey, themeTagQuery } from "@/components/FilterBar";
import { GlobeView } from "@/components/GlobeView";
import { StoryPanel } from "@/components/StoryPanel";
import { fetchStats, fetchStories, fetchStory, searchStories } from "@/services/api";
import type { Lang, StoryFull, StoryLight } from "@/types";

function matchesFilters(s: StoryLight, theme: ThemeKey, era: EraKey): boolean {
  const tags = s.tags.map((t) => t.toLowerCase());
  const tw = themeTagQuery(theme);
  if (tw && !tags.some((t) => t.includes(tw))) return false;
  const ew = eraTagQuery(era);
  if (ew && !tags.some((t) => t.includes(ew))) return false;
  return true;
}

export default function App() {
  const [langUI, setLangUI] = useState<Lang>("zh");
  const [stories, setStories] = useState<StoryLight[]>([]);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [summary, setSummary] = useState<{ total_stories: number; countries: number } | null>(null);
  const [countryGroups, setCountryGroups] = useState<
    { country: string; count: number; stories: StoryLight[] }[]
  >([]);

  const [theme, setTheme] = useState<ThemeKey>("all");
  const [era, setEra] = useState<EraKey>("all");
  const [showLabels, setShowLabels] = useState(true);
  const [showLines, setShowLines] = useState(false);

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<StoryFull | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [hoverStory, setHoverStory] = useState<StoryLight | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);

  const [headerSearch, setHeaderSearch] = useState("");
  const [searchBusy, setSearchBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [st, stat] = await Promise.all([fetchStories(), fetchStats()]);
        if (cancelled) return;
        setStories(st);
        setCountryGroups(stat.countries);
        setSummary({ total_stories: stat.total_stories, countries: stat.country_count });
        setStatsError(null);
      } catch (e) {
        if (!cancelled) setStatsError(e instanceof Error ? e.message : "Failed to load data");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(
    () => stories.filter((s) => matchesFilters(s, theme, era)),
    [stories, theme, era],
  );

  const maxCount = useMemo(
    () => countryGroups.reduce((m, g) => Math.max(m, g.count), 0),
    [countryGroups],
  );

  const highlightCountry = useMemo(() => {
    if (hoverStory) return hoverStory.country;
    if (selectedCountry) return selectedCountry;
    return null;
  }, [hoverStory, selectedCountry]);

  const overlayTitle = langUI === "zh" ? "世界神话地图" : "World Mythology Map";
  const subtitle =
    summary && !statsError
      ? langUI === "zh"
        ? `${summary.total_stories} 个故事 · ${summary.countries} 个国家/地区`
        : `${summary.total_stories} stories · ${summary.countries} countries`
      : "";

  const openStory = useCallback(async (id: number) => {
    setSelectedId(id);
    setDetail(null);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const full = await fetchStory(id);
      setDetail(full);
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : "Failed to load story");
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const closeStory = useCallback(() => {
    setSelectedId(null);
    setDetail(null);
    setDetailError(null);
  }, []);

  const runHeaderSearch = useCallback(async () => {
    const q = headerSearch.trim();
    if (!q) return;
    setSearchBusy(true);
    try {
      const hits = await searchStories(q);
      if (hits.length) await openStory(hits[0].id);
    } catch (e) {
      setDetailError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setSearchBusy(false);
    }
  }, [headerSearch, openStory]);

  const sidebarStories = useMemo(() => {
    if (!selectedCountry) return filtered;
    return filtered.filter((s) => s.country === selectedCountry);
  }, [filtered, selectedCountry]);

  const sidebarGroups = useMemo(() => {
    const m = new Map<string, StoryLight[]>();
    for (const s of sidebarStories) {
      const arr = m.get(s.country) ?? [];
      arr.push(s);
      m.set(s.country, arr);
    }
    return [...m.entries()]
      .map(([country, st]) => ({
        country,
        count: st.length,
        stories: st,
      }))
      .sort((a, b) => b.count - a.count || a.country.localeCompare(b.country));
  }, [sidebarStories]);

  return (
    <div className="relative flex h-full w-full flex-col bg-slate-950 text-slate-100 md:flex-row">
      <div className="relative flex min-h-[55vh] flex-1 flex-col md:min-h-0">
        <header className="pointer-events-none absolute left-0 right-0 top-0 z-20 flex items-center justify-between gap-2 px-3 py-3 md:px-5">
          <button
            type="button"
            className="pointer-events-auto rounded-xl p-2 text-slate-400 hover:bg-slate-900/60 hover:text-slate-100"
            aria-label="Back"
          >
            ←
          </button>
          <div className="pointer-events-none text-center">
            <h1 className="text-sm font-semibold tracking-wide text-slate-100 drop-shadow md:text-base">
              {overlayTitle}
            </h1>
            {subtitle ? (
              <p className="mt-0.5 text-[11px] text-sky-200/80 drop-shadow md:text-xs">{subtitle}</p>
            ) : null}
          </div>
          <div className="pointer-events-auto flex items-center gap-1">
            <button
              type="button"
              className="rounded-xl p-2 text-slate-400 hover:bg-slate-900/60 hover:text-slate-100"
              title="Layers"
              aria-label="Layers"
            >
              ⧉
            </button>
            <div className="hidden items-center gap-1 sm:flex">
              <input
                value={headerSearch}
                onChange={(e) => setHeaderSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && runHeaderSearch()}
                placeholder={langUI === "zh" ? "语义搜索…" : "Semantic search…"}
                className="w-36 rounded-xl border border-slate-700/80 bg-slate-950/70 px-2 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 md:w-44"
              />
              <button
                type="button"
                onClick={runHeaderSearch}
                disabled={searchBusy}
                className="rounded-xl p-2 text-slate-300 hover:bg-slate-900/60 disabled:opacity-50"
                aria-label="Search"
              >
                🔍
              </button>
            </div>
            <button
              type="button"
              className="rounded-xl p-2 text-slate-400 hover:bg-slate-900/60 hover:text-slate-100"
              aria-label="Share"
            >
              ↗
            </button>
          </div>
        </header>

        {statsError ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/90 p-6 text-center text-sm text-red-300">
            {statsError}
          </div>
        ) : (
          <GlobeView
            stories={filtered}
            selectedId={selectedId}
            onSelect={(id) => void openStory(id)}
            onHover={setHoverStory}
            showLabels={showLabels}
            showLines={showLines}
            highlightCountry={highlightCountry}
          />
        )}

        <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-20 flex justify-center pb-3 md:pb-4">
          <FilterBar
            lang={langUI}
            theme={theme}
            era={era}
            showLabels={showLabels}
            showLines={showLines}
            onTheme={setTheme}
            onEra={setEra}
            onToggleLabels={setShowLabels}
            onToggleLines={setShowLines}
          />
        </div>
      </div>

      <div className="relative z-10 flex w-full shrink-0 border-t border-slate-800/80 bg-slate-950/30 p-2 md:w-auto md:border-l md:border-t-0 md:p-3">
        <CountrySidebar
          groups={sidebarGroups}
          lang={langUI}
          selectedCountry={selectedCountry}
          onSelectCountry={setSelectedCountry}
          onPickStory={(id) => void openStory(id)}
          maxCount={maxCount}
        />
      </div>

      <div className="pointer-events-none absolute bottom-28 left-3 right-[min(92vw,360px)] z-[25] flex flex-wrap items-center gap-2 md:bottom-32 md:left-6">
        <div className="pointer-events-auto glass-panel flex items-center gap-2 px-2 py-1.5 text-[11px] text-slate-400">
          <span>{langUI === "zh" ? "界面" : "UI"}</span>
          <button
            type="button"
            onClick={() => setLangUI("zh")}
            className={`rounded-full px-2 py-0.5 ${langUI === "zh" ? "bg-sky-600 text-white" : "hover:bg-slate-800"}`}
          >
            中文
          </button>
          <button
            type="button"
            onClick={() => setLangUI("en")}
            className={`rounded-full px-2 py-0.5 ${langUI === "en" ? "bg-sky-600 text-white" : "hover:bg-slate-800"}`}
          >
            EN
          </button>
        </div>
      </div>

      <StoryPanel
        story={detail}
        lang={langUI}
        onClose={closeStory}
        onLang={setLangUI}
        loading={detailLoading}
        error={detailError}
      />
    </div>
  );
}
