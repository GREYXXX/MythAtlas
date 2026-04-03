export type Lang = "en" | "zh";

export interface StoryLight {
  id: number;
  title_en: string;
  title_zh: string;
  lat: number;
  lng: number;
  country: string;
  emoji: string;
  tags: string[];
}

export interface StoryFull extends StoryLight {
  content_en: string;
  content_zh: string;
}

export interface CountryGroup {
  country: string;
  count: number;
  stories: StoryLight[];
}

export interface StatsResponse {
  total_stories: number;
  country_count: number;
  countries: CountryGroup[];
}

export interface SearchHit {
  id: number;
  title_en: string;
  title_zh: string;
  country: string;
  emoji: string;
  score: number;
  method: string;
}
