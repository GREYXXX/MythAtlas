import type { Lang, StoryFull } from "@/types";

type Props = {
  story: StoryFull | null;
  lang: Lang;
  onClose: () => void;
  onLang: (l: Lang) => void;
  loading?: boolean;
  error?: string | null;
};

export function StoryPanel({ story, lang, onClose, onLang, loading, error }: Props) {
  if (!story && !loading && !error) return null;

  const title = story ? (lang === "zh" ? story.title_zh : story.title_en) : "";
  const body = story ? (lang === "zh" ? story.content_zh : story.content_en) : "";

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30 flex justify-center p-3 md:p-6">
      <div className="glass-panel pointer-events-auto max-h-[min(70vh,560px)] w-full max-w-lg overflow-y-auto border-slate-700/90 bg-slate-950/95 p-4 shadow-2xl backdrop-blur-xl md:p-5">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="text-3xl leading-none md:text-4xl">{story?.emoji ?? "📖"}</div>
            <div>
              <h2 className="text-lg font-semibold text-slate-50 md:text-xl">{title}</h2>
              {story ? (
                <p className="mt-1 text-xs text-slate-400">
                  <span className="text-slate-300">📍</span> {story.country}
                </p>
              ) : null}
              {story?.tags?.length ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {story.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[11px] text-slate-300 ring-1 ring-slate-700/80"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-sm text-slate-400 hover:bg-slate-800/80 hover:text-slate-100"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {loading ? (
          <div className="py-8 text-center text-sm text-slate-400">Loading…</div>
        ) : error ? (
          <div className="rounded-lg border border-red-900/50 bg-red-950/40 p-3 text-sm text-red-200">{error}</div>
        ) : (
          <p className="text-sm leading-relaxed text-slate-200 md:text-[15px]">{body}</p>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-700/60 pt-3">
          <span className="text-[11px] uppercase tracking-wide text-slate-500">Language</span>
          {(["zh", "en"] as const).map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => onLang(l)}
              className={`rounded-full px-3 py-1 text-xs font-medium ring-1 transition ${
                lang === l
                  ? "bg-sky-600/90 text-white ring-sky-400/50"
                  : "bg-slate-900/60 text-slate-300 ring-slate-700 hover:bg-slate-800"
              }`}
            >
              {l === "zh" ? "中文" : "English"}
            </button>
          ))}
        </div>

        <p className="mt-3 text-[10px] text-slate-500">内容可能使用 AI 技术生成 · Content may be AI-assisted</p>
      </div>
    </div>
  );
}
