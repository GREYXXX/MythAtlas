/** Natural Earth populated places (simple) GeoJSON feature */
export type NEPlaceFeature = {
  type: "Feature";
  properties: {
    name?: string;
    nameascii?: string | null;
    latitude: number;
    longitude: number;
    pop_max: number;
    worldcity?: number;
  };
};

/** Prefer ASCII / Latin-script names; strip CJK if `nameascii` is missing. */
export function englishPlaceName(p: NEPlaceFeature["properties"]): string {
  const ascii = p.nameascii != null ? String(p.nameascii).trim() : "";
  if (ascii.length > 0) return ascii;
  const n = p.name != null ? String(p.name).trim() : "";
  if (!n) return "";
  const stripped = n
    .replace(/[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]+/g, "")
    .trim();
  return stripped.length > 0 ? stripped : n;
}

/**
 * Fewer cities when less zoomed in; more when closer. Altitude: lower = closer.
 */
export function filterPlacesForAltitude(features: NEPlaceFeature[], altitude: number): NEPlaceFeature[] {
  if (altitude >= 1.48) return [];
  const pop = (f: NEPlaceFeature) => f.properties.pop_max ?? 0;
  if (altitude < 0.92) return features.filter((f) => pop(f) >= 120_000);
  if (altitude < 1.15) return features.filter((f) => pop(f) >= 500_000);
  return features.filter((f) => pop(f) >= 1_400_000 || f.properties.worldcity === 1);
}
