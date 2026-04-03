import { useCallback, useMemo } from "react";
import Globe from "react-globe.gl";
import type { StoryLight } from "@/types";
import { useElementSize } from "@/hooks/useElementSize";

type Props = {
  stories: StoryLight[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onHover: (story: StoryLight | null) => void;
  showLabels: boolean;
  showLines: boolean;
  highlightCountry: string | null;
};

export function GlobeView({
  stories,
  selectedId,
  onSelect,
  onHover,
  showLabels,
  showLines,
  highlightCountry,
}: Props) {
  const { ref: setContainer, size } = useElementSize<HTMLDivElement>();

  const data = useMemo(
    () =>
      stories.map((s) => ({
        ...s,
        __size: s.id === selectedId ? 1.65 : 1.15,
      })),
    [stories, selectedId],
  );

  const htmlElement = useCallback(
    (d: object) => {
      const s = d as StoryLight & { __size: number };
      const el = document.createElement("div");
      el.style.display = "flex";
      el.style.flexDirection = "column";
      el.style.alignItems = "center";
      el.style.pointerEvents = "auto";
      el.style.cursor = "pointer";
      el.style.userSelect = "none";

      const emoji = document.createElement("div");
      emoji.textContent = s.emoji;
      emoji.style.fontSize = `${14 + s.__size * 10}px`;
      emoji.style.lineHeight = "1";
      emoji.style.filter = "drop-shadow(0 0 6px rgba(0,0,0,0.85))";
      emoji.style.transition = "transform 160ms ease";

      if (showLabels) {
        const cap = document.createElement("div");
        cap.textContent = s.country;
        cap.style.marginTop = "4px";
        cap.style.fontSize = "10px";
        cap.style.color = "rgba(226,232,240,0.92)";
        cap.style.maxWidth = "120px";
        cap.style.textAlign = "center";
        cap.style.whiteSpace = "nowrap";
        cap.style.overflow = "hidden";
        cap.style.textOverflow = "ellipsis";
        cap.style.textShadow = "0 0 8px rgba(0,0,0,0.9)";
        el.appendChild(emoji);
        el.appendChild(cap);
      } else {
        el.appendChild(emoji);
      }

      el.onmouseenter = () => {
        emoji.style.transform = "scale(1.12)";
        onHover(s);
      };
      el.onmouseleave = () => {
        emoji.style.transform = "scale(1)";
        onHover(null);
      };
      el.onclick = (ev) => {
        ev.stopPropagation();
        onSelect(s.id);
      };

      return el;
    },
    [onHover, onSelect, showLabels],
  );

  const globeImageUrl = "//unpkg.com/three-globe/example/img/earth-night.jpg";
  const backgroundImageUrl = "//unpkg.com/three-globe/example/img/night-sky.png";

  return (
    <div ref={setContainer} className="relative h-full min-h-[320px] w-full">
      <Globe
        width={size.width}
        height={size.height}
        backgroundColor="rgba(2,6,23,0)"
        backgroundImageUrl={backgroundImageUrl}
        globeImageUrl={globeImageUrl}
        bumpImageUrl="//unpkg.com/three-globe/example/img/earth-topology.png"
        showAtmosphere
        atmosphereColor="rgba(56,189,248,0.22)"
        atmosphereAltitude={0.18}
        showGraticules={showLines}
        htmlElementsData={data}
        htmlLat={(d: object) => (d as StoryLight).lat}
        htmlLng={(d: object) => (d as StoryLight).lng}
        htmlAltitude={0.012}
        htmlElement={htmlElement}
        htmlTransitionDuration={400}
        onGlobeClick={() => onHover(null)}
      />
      {highlightCountry ? (
        <div className="pointer-events-none absolute left-1/2 top-6 z-10 -translate-x-1/2 text-center">
          <div className="glass-panel px-4 py-2 text-xs text-slate-100 md:text-sm">
            <div className="font-medium tracking-wide text-sky-200/90">{highlightCountry}</div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
