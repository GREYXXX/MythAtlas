/**
 * Strips CJK / Hangul / Japanese kana from labels like "China 中国" for English-only UI.
 * Internal grouping keys stay unchanged (still the full API string).
 */
export function formatCountryForDisplay(country: string): string {
  return country
    .replace(/[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]+/g, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+([,/])/g, "$1")
    .trim();
}
