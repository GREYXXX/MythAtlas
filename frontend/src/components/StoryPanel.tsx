import type { ReactNode } from "react";
import type { Lang, StoryFull } from "@/types";
import { formatCountryForDisplay } from "@/utils/countryDisplay";

type Props = {
  story: StoryFull | null;
  lang: Lang;
  onClose: () => void;
  onLang: (l: Lang) => void;
  loading?: boolean;
  error?: string | null;
};

const URL_RE = /https?:\/\/[^\s<>"']+/gi;

function linkifyText(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  const re = new RegExp(URL_RE.source, URL_RE.flags);
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) {
      out.push(text.slice(last, m.index));
    }
    let href = m[0];
    while (/[),.;:]+$/.test(href)) {
      href = href.slice(0, -1);
    }
    out.push(
      <a
        key={key++}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="break-all text-sky-300 underline decoration-sky-500/60 underline-offset-[3px] transition hover:text-sky-200 hover:decoration-sky-400"
      >
        {href}
      </a>,
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) {
    out.push(text.slice(last));
  }
  return out.length ? out : [text];
}

function StoryProse({ text, lang }: { text: string; lang: Lang }) {
  const blocks = text
    .trim()
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean);

  if (blocks.length === 0) {
    return null;
  }

  const isEn = lang === "en";
  const bodyClass = isEn
    ? "font-storyEn text-[0.9375rem] font-normal leading-[1.72] tracking-[0.01em] text-slate-200/95 md:text-[1.0625rem] whitespace-pre-line text-pretty"
    : "font-storyZh text-[0.9375rem] font-normal leading-[1.65] tracking-[0.01em] text-slate-200/95 md:text-base whitespace-pre-line";

  return (
    <div className="space-y-4 border-t border-slate-800/90 pt-5">
      {blocks.map((block, i) => (
        <p key={i} className={bodyClass} lang={isEn ? "en" : "zh-CN"}>
          {linkifyText(block)}
        </p>
      ))}
    </div>
  );
}

export function StoryPanel({ story, lang, onClose, onLang, loading, error }: Props) {
  if (!story && !loading && !error) return null;

  const title = story ? (lang === "zh" ? story.title_zh : story.title_en) : "";
  const titleDisplay =
    title ||
    (loading ? (lang === "zh" ? "加载中…" : "Loading…") : "") ||
    (error && !story ? (lang === "zh" ? "无法加载" : "Unable to load") : "");
  const body = story ? (lang === "zh" ? story.content_zh : story.content_en) : "";
  const closeLabel = lang === "zh" ? "关闭" : "Close";

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-30 flex justify-center p-3 md:p-6">
      <div className="pointer-events-auto max-h-[min(72vh,580px)] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-700/50 bg-[#121826]/97 p-5 shadow-2xl shadow-black/40 backdrop-blur-xl md:p-7">
        <header className="flex items-start justify-between gap-4">
          <div className="flex min-w-0 flex-1 items-start gap-3.5">
            <div className="shrink-0 text-[2.25rem] leading-none md:text-[2.6rem]" aria-hidden>
              {story?.emoji ?? "📖"}
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="font-sans text-lg font-semibold leading-snug tracking-tight text-slate-50 md:text-xl">
                {titleDisplay}
              </h2>
              {story ? (
                <p className="mt-2 font-sans text-[11px] font-medium uppercase tracking-[0.2em] text-slate-500">
                  <span className="mr-1.5 normal-case tracking-normal text-slate-400" aria-hidden>
                    📍
                  </span>
                  {formatCountryForDisplay(story.country)}
                </p>
              ) : null}
              {story?.tags?.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {story.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-full border border-slate-600/55 bg-slate-950/40 px-2.5 py-1 font-sans text-[10px] font-medium uppercase tracking-wider text-slate-400"
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
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-700/60 bg-slate-900/50 text-base text-slate-500 transition hover:border-slate-600 hover:bg-slate-800/80 hover:text-slate-200"
            aria-label={closeLabel}
          >
            ✕
          </button>
        </header>

        {loading ? (
          <div className="py-10 text-center font-sans text-sm text-slate-500">Loading…</div>
        ) : error ? (
          <div className="mt-4 rounded-xl border border-red-900/45 bg-red-950/35 p-4 font-sans text-sm leading-relaxed text-red-100">
            {error}
          </div>
        ) : (
          <StoryProse text={body} lang={lang} />
        )}

        <footer className="mt-6 border-t border-slate-800/90 pt-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-sans text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              {lang === "zh" ? "语言" : "Language"}
            </span>
            {(["zh", "en"] as const).map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => onLang(l)}
                className={`rounded-full border px-3 py-1.5 font-sans text-xs font-medium transition ${
                  lang === l
                    ? "border-sky-500/60 bg-sky-600 text-white shadow-sm shadow-sky-900/30"
                    : "border-slate-600/50 bg-transparent text-slate-400 hover:border-slate-500 hover:bg-slate-800/50 hover:text-slate-200"
                }`}
              >
                {l === "zh" ? "中文" : "English"}
              </button>
            ))}
          </div>
          <p className="mt-3 font-sans text-[10px] leading-relaxed text-slate-600">
            内容可能使用 AI 技术生成 · Content may be AI-assisted
          </p>
        </footer>
      </div>
    </div>
  );
}
