export type ThemeKey =
  | "all"
  | "sun"
  | "flood"
  | "fire"
  | "dragon"
  | "love"
  | "moon"
  | "princess";

export type EraKey = "all" | "ancient" | "classical" | "medieval" | "modern";

const THEMES: { key: ThemeKey; en: string; zh: string; tag?: string }[] = [
  { key: "all", en: "All", zh: "全部" },
  { key: "sun", en: "Sun", zh: "太阳", tag: "sun" },
  { key: "flood", en: "Flood", zh: "洪水", tag: "flood" },
  { key: "fire", en: "Fire", zh: "火", tag: "fire" },
  { key: "dragon", en: "Dragon", zh: "龙", tag: "dragon" },
  { key: "love", en: "Love", zh: "爱情", tag: "love" },
  { key: "moon", en: "Moon", zh: "月亮", tag: "moon" },
  { key: "princess", en: "Princess", zh: "公主", tag: "princess" },
];

const ERAS: { key: EraKey; en: string; zh: string; tag?: string }[] = [
  { key: "all", en: "All Eras", zh: "全部年代" },
  { key: "ancient", en: "Ancient", zh: "远古", tag: "ancient" },
  { key: "classical", en: "Classical", zh: "古代", tag: "classical" },
  { key: "medieval", en: "Medieval", zh: "中世纪", tag: "medieval" },
  { key: "modern", en: "Modern", zh: "近代", tag: "modern" },
];

type Props = {
  lang: "en" | "zh";
  theme: ThemeKey;
  era: EraKey;
  showLabels: boolean;
  showLines: boolean;
  onTheme: (t: ThemeKey) => void;
  onEra: (e: EraKey) => void;
  onToggleLabels: (v: boolean) => void;
  onToggleLines: (v: boolean) => void;
};

export function FilterBar({
  lang,
  theme,
  era,
  showLabels,
  showLines,
  onTheme,
  onEra,
  onToggleLabels,
  onToggleLines,
}: Props) {
  const L = (o: { en: string; zh: string }) => (lang === "zh" ? o.zh : o.en);

  return (
    <div className="glass-panel pointer-events-auto max-w-[min(96vw,1100px)] space-y-2 px-2 py-2 md:px-3">
      <div className="flex gap-1.5 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {THEMES.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => onTheme(t.key)}
            className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-medium ring-1 transition md:text-[13px] ${
              theme === t.key
                ? "bg-sky-600/85 text-white ring-sky-400/50"
                : "bg-slate-900/55 text-slate-300 ring-slate-700 hover:bg-slate-800/80"
            }`}
          >
            {L(t)}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex min-w-0 flex-1 gap-1.5 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {ERAS.map((e) => (
            <button
              key={e.key}
              type="button"
              onClick={() => onEra(e.key)}
              className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-medium ring-1 transition md:text-[13px] ${
                era === e.key
                  ? "bg-violet-600/80 text-white ring-violet-400/45"
                  : "bg-slate-900/55 text-slate-300 ring-slate-700 hover:bg-slate-800/80"
              }`}
            >
              {L(e)}
            </button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-3 border-l border-slate-700/60 pl-3">
          <Toggle label="Labels" lang={lang} value={showLabels} onChange={onToggleLabels} />
          <Toggle label="Lines" lang={lang} value={showLines} onChange={onToggleLines} />
        </div>
      </div>
    </div>
  );
}

function Toggle({
  label,
  lang,
  value,
  onChange,
}: {
  label: string;
  lang: "en" | "zh";
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  const text =
    label === "Labels"
      ? lang === "zh"
        ? "标签"
        : "Labels"
      : lang === "zh"
        ? "经纬线"
        : "Lines";
  return (
    <label className="flex cursor-pointer items-center gap-2 text-[11px] text-slate-400">
      <span>{text}</span>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={`relative h-6 w-11 rounded-full transition ${
          value ? "bg-sky-600/90" : "bg-slate-700/90"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${
            value ? "left-5" : "left-0.5"
          }`}
        />
      </button>
    </label>
  );
}

export function themeTagQuery(theme: ThemeKey): string | undefined {
  const row = THEMES.find((t) => t.key === theme);
  return row?.tag;
}

export function eraTagQuery(era: EraKey): string | undefined {
  const row = ERAS.find((e) => e.key === era);
  return row?.tag;
}
