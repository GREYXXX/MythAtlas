import Globe, { type GlobeMethods } from "react-globe.gl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  LinearFilter,
  LinearMipmapLinearFilter,
  Mesh,
  MeshStandardMaterial,
} from "three";
import type { Lang, StoryLight } from "@/types";
import { useElementSize } from "@/hooks/useElementSize";
import { formatCountryForDisplay } from "@/utils/countryDisplay";
import {
  englishPlaceName,
  filterPlacesForAltitude,
  type NEPlaceFeature,
} from "@/utils/cityLabels";

type StoryMarkerData = StoryLight & {
  __size: number;
  __clusterCount?: number;
};

type Props = {
  stories: StoryLight[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onHover: (story: StoryLight | null) => void;
  showLines: boolean;
  highlightCountry: string | null;
  isolateStoryMarker?: boolean;
  showCityNames?: boolean;
  lang?: Lang;
};

const ALT_MIN = 0.42;
const ALT_MAX = 6.2;
// Debounce LOD updates so they don't fire on every drag/zoom frame
const LOD_DEBOUNCE_MS = 150;

function gridStepForAltitude(altitude: number): number {
  if (altitude >= 3.8) return 18;
  if (altitude >= 2.8) return 9;
  if (altitude >= 2.0) return 4.5;
  return 0;
}

function clusterStoriesForLod(stories: StoryLight[], stepDeg: number): StoryLight[] {
  if (stepDeg <= 0 || stories.length <= 1) return stories;
  const buckets = new Map<string, StoryLight[]>();
  for (const s of stories) {
    const gi = Math.round(s.lat / stepDeg);
    const gj = Math.round(s.lng / stepDeg);
    const key = `${gi},${gj}`;
    const list = buckets.get(key) ?? [];
    list.push(s);
    buckets.set(key, list);
  }
  const out: StoryLight[] = [];
  for (const group of buckets.values()) {
    if (group.length === 1) {
      out.push(group[0]);
    } else {
      const lat = group.reduce((a, s) => a + s.lat, 0) / group.length;
      const lng = group.reduce((a, s) => a + s.lng, 0) / group.length;
      const sorted = [...group].sort((a, b) => a.id - b.id);
      out.push({
        ...sorted[0],
        lat,
        lng,
        __clusterCount: group.length,
      } as StoryLight & { __clusterCount: number });
    }
  }
  return out;
}

function tuneGlobeTextures(globe: GlobeMethods) {
  const maxAniso = globe.renderer().capabilities.getMaxAnisotropy?.() ?? 8;
  globe.scene().traverse((obj) => {
    const mesh = obj as Mesh;
    if (!mesh.isMesh) return;
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const m of mats) {
      const mat = m as MeshStandardMaterial;
      if (!mat.map) continue;
      mat.map.anisotropy = maxAniso;
      mat.map.minFilter = LinearMipmapLinearFilter;
      mat.map.magFilter = LinearFilter;
      mat.map.needsUpdate = true;
    }
  });
}

export function GlobeView({
  stories,
  selectedId,
  onSelect,
  onHover,
  showLines,
  highlightCountry,
  isolateStoryMarker = false,
  showCityNames = false,
  lang = "en",
}: Props) {
  const { ref: setContainer, size } = useElementSize<HTMLDivElement>();
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const [camAltitude, setCamAltitude] = useState(2.2);
  const [cityFeatures, setCityFeatures] = useState<NEPlaceFeature[]>([]);
  const lodDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const visibleStories = useMemo(() => {
    if (isolateStoryMarker && selectedId != null) {
      return stories.filter((s) => s.id === selectedId);
    }
    return stories;
  }, [stories, isolateStoryMarker, selectedId]);

  const lodStories = useMemo(() => {
    if (isolateStoryMarker) return visibleStories;
    const step = gridStepForAltitude(camAltitude);
    return clusterStoriesForLod(visibleStories, step);
  }, [visibleStories, isolateStoryMarker, camAltitude]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/data/ne_110m_populated_places_simple.geojson");
        if (!res.ok) return;
        const geo = (await res.json()) as { features?: NEPlaceFeature[] };
        if (!cancelled && Array.isArray(geo.features)) {
          setCityFeatures(geo.features.filter((f) => f?.properties?.latitude != null));
        }
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, []);

  const labelsData = useMemo(() => {
    if (!showCityNames || isolateStoryMarker || cityFeatures.length === 0) return [];
    return filterPlacesForAltitude(cityFeatures, camAltitude).filter(
      (f) => englishPlaceName(f.properties).length > 0,
    );
  }, [showCityNames, cityFeatures, camAltitude, isolateStoryMarker]);

  const data = useMemo(
    () =>
      lodStories.map((s) => ({
        ...s,
        __size: s.id === selectedId ? 1.65 : 1.15,
      })) as StoryMarkerData[],
    [lodStories, selectedId],
  );

  const zoomByFactor = useCallback((factor: number) => {
    const g = globeRef.current;
    if (!g) return;
    const pov = g.pointOfView();
    const next = Math.min(ALT_MAX, Math.max(ALT_MIN, pov.altitude * factor));
    g.pointOfView({ lat: pov.lat, lng: pov.lng, altitude: next }, 420);
  }, []);

  const zoomIntoCluster = useCallback((lat: number, lng: number) => {
    const g = globeRef.current;
    if (!g) return;
    const pov = g.pointOfView();
    const nextAlt = Math.max(ALT_MIN, pov.altitude * 0.58);
    g.pointOfView({ lat, lng, altitude: nextAlt }, 520);
  }, []);

  const htmlElement = useCallback(
    (d: object) => {
      const s = d as StoryMarkerData;
      const el = document.createElement("div");
      el.style.cssText = "display:flex;flex-direction:column;align-items:center;pointer-events:auto;cursor:pointer;user-select:none;";

      const emojiWrap = document.createElement("div");
      emojiWrap.style.position = "relative";
      emojiWrap.style.display = "inline-block";

      const emoji = document.createElement("div");
      emoji.textContent = s.emoji;
      // Larger base size + stronger drop-shadow to pop against dark globe
      emoji.style.cssText = `font-size:${14 + s.__size * 10}px;line-height:1;transition:transform 160ms ease;filter:drop-shadow(0 0 5px rgba(0,0,0,0.9)) drop-shadow(0 0 10px rgba(255,255,255,0.15));`;

      emojiWrap.appendChild(emoji);

      const cc = s.__clusterCount;
      if (cc != null && cc > 1) {
        const badge = document.createElement("div");
        badge.textContent = String(cc);
        badge.style.cssText =
          "position:absolute;top:-7px;right:-10px;min-width:18px;height:18px;border-radius:9999px;background:#0284c7;color:#f8fafc;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;padding:0 5px;box-shadow:0 0 8px rgba(0,0,0,0.85);pointer-events:none;";
        emojiWrap.appendChild(badge);
      }

      el.appendChild(emojiWrap);

      el.onmouseenter = () => {
        emoji.style.transform = "scale(1.2)";
        if (cc == null || cc <= 1) onHover(s);
      };
      el.onmouseleave = () => {
        emoji.style.transform = "scale(1)";
        if (cc == null || cc <= 1) onHover(null);
      };
      el.onclick = (ev) => {
        ev.stopPropagation();
        if (cc != null && cc > 1) {
          zoomIntoCluster(s.lat, s.lng);
          onHover(null);
        } else {
          onSelect(s.id);
        }
      };

      return el;
    },
    [onHover, onSelect, zoomIntoCluster],
  );

  const onGlobeReady = useCallback(() => {
    const g = globeRef.current;
    if (!g) return;
    setCamAltitude(g.pointOfView().altitude);
    tuneGlobeTextures(g);
    g.renderer().setPixelRatio(Math.min(window.devicePixelRatio, 2));
  }, []);

  // Debounced — LOD only recalculates after the user stops zooming/panning
  const onZoom = useCallback((pov: { lat: number; lng: number; altitude: number }) => {
    if (lodDebounceRef.current) clearTimeout(lodDebounceRef.current);
    lodDebounceRef.current = setTimeout(() => setCamAltitude(pov.altitude), LOD_DEBOUNCE_MS);
  }, []);

  // Night earth: dark with city lights — emoji pop against the dark surface
  const globeImageUrl = "//cdn.jsdelivr.net/npm/three-globe@2.45.1/example/img/earth-night.jpg";
  const backgroundImageUrl = "//unpkg.com/three-globe/example/img/night-sky.png";

  const zoomInLabel = lang === "zh" ? "放大" : "Zoom in";
  const zoomOutLabel = lang === "zh" ? "缩小" : "Zoom out";

  return (
    <div ref={setContainer} className="relative h-full min-h-[320px] w-full">
      <Globe
        ref={globeRef}
        width={size.width}
        height={size.height}
        backgroundColor="rgba(2,6,23,0)"
        backgroundImageUrl={backgroundImageUrl}
        globeImageUrl={globeImageUrl}
        globeCurvatureResolution={2}
        labelsData={labelsData}
        labelLat={(d: object) => (d as NEPlaceFeature).properties.latitude}
        labelLng={(d: object) => (d as NEPlaceFeature).properties.longitude}
        labelText={(d: object) => englishPlaceName((d as NEPlaceFeature).properties)}
        labelColor={() => "rgba(200, 220, 255, 0.65)"}
        labelAltitude={0.004}
        labelSize={(d: object) => {
          const pop = (d as NEPlaceFeature).properties.pop_max;
          const base = Math.sqrt(Math.max(pop, 1)) * 2.1e-4;
          return Math.min(0.42, Math.max(0.07, base));
        }}
        labelDotRadius={(d: object) => {
          const pop = (d as NEPlaceFeature).properties.pop_max;
          return Math.min(0.12, Math.sqrt(Math.max(pop, 1)) * 1.1e-4);
        }}
        labelIncludeDot
        labelResolution={2}
        labelsTransitionDuration={380}
        showAtmosphere
        atmosphereColor="rgba(80,160,255,0.2)"
        atmosphereAltitude={0.2}
        showGraticules={showLines}
        htmlElementsData={data}
        htmlLat={(d: object) => (d as StoryLight).lat}
        htmlLng={(d: object) => (d as StoryLight).lng}
        htmlAltitude={0.012}
        htmlElement={htmlElement}
        htmlTransitionDuration={400}
        onGlobeClick={() => onHover(null)}
        onGlobeReady={onGlobeReady}
        onZoom={onZoom}
      />
      <div className="pointer-events-auto absolute right-3 top-1/2 z-[22] flex -translate-y-1/2 flex-col gap-0.5 rounded-xl border border-slate-700/85 bg-slate-950/88 p-1 shadow-lg backdrop-blur-sm md:right-4">
        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-lg font-semibold text-slate-100 hover:bg-sky-600/35 active:bg-sky-600/50"
          aria-label={zoomInLabel}
          title={zoomInLabel}
          onClick={() => zoomByFactor(0.72)}
        >
          +
        </button>
        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-lg font-semibold text-slate-100 hover:bg-sky-600/35 active:bg-sky-600/50"
          aria-label={zoomOutLabel}
          title={zoomOutLabel}
          onClick={() => zoomByFactor(1.38)}
        >
          −
        </button>
      </div>
      {highlightCountry ? (
        <div className="pointer-events-none absolute left-1/2 top-6 z-10 -translate-x-1/2 text-center">
          <div className="glass-panel px-4 py-2 text-xs text-slate-100 md:text-sm">
            <div className="font-medium tracking-wide text-sky-200/90">
              {formatCountryForDisplay(highlightCountry)}
            </div>
          </div>
        </div>
      ) : null}
      {labelsData.length > 0 ? (
        <div className="pointer-events-none absolute bottom-[5.25rem] left-2 z-[21] max-w-[11rem] font-sans text-[9px] leading-tight text-slate-600 md:bottom-[5.75rem] md:text-[10px]">
          <a
            href="https://www.naturalearthdata.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="pointer-events-auto text-slate-500 underline decoration-slate-700 underline-offset-2 hover:text-slate-400"
          >
            Natural Earth
          </a>
          <span className="text-slate-600"> — populated places (English names)</span>
        </div>
      ) : null}
    </div>
  );
}
