export type SourceType = 'torznab' | 'newznab' | 'rss' | 'manifest' | 'generic_http';
export type SourceStatus = 'unknown' | 'active' | 'degraded' | 'dead';
export type Category = 'movie' | 'series' | 'anime';
export type LanguageTarget = 'ita' | 'ger' | 'multi';

export interface SourceScore {
  id: string;
  source_id: string;
  overall_score: number;
  italian_score: number;
  german_score: number;
  speed_score: number;
  reliability_score: number;
  trust_score: number;
  calculated_at: string;
}

export interface SourceTest {
  id: string;
  source_id: string;
  timestamp: string;
  success: boolean;
  response_time_ms: number | null;
  http_status: number | null;
  notes: string | null;
  tester_type: string | null;
}

export interface Source {
  id: string;
  name: string;
  url: string;
  source_type: SourceType;
  status: SourceStatus;
  requires_auth: boolean;
  last_checked: string | null;
  created_at: string;
  updated_at: string;
  latest_score: SourceScore | null;
}

export interface SourceDetail extends Source {
  recent_tests: SourceTest[];
}

export interface SourceCreate {
  name: string;
  url: string;
  source_type: SourceType;
  requires_auth: boolean;
  auth_key?: string;
}

export interface Stats {
  total: number;
  active: number;
  degraded: number;
  dead: number;
  unknown: number;
  avg_overall_score: number;
  recent_tests: SourceTest[];
}

// ── Benchmark ────────────────────────────────────────────────────────────────

export interface BenchmarkTitle {
  id: string;
  title: string;
  imdb_id: string | null;
  tmdb_id: string | null;
  category: Category;
  language_target: LanguageTarget;
  year: number | null;
  created_at: string;
}

export interface BenchmarkTitleCreate {
  title: string;
  imdb_id?: string;
  tmdb_id?: string;
  category: Category;
  language_target: LanguageTarget;
  year?: number;
}

export interface BenchmarkResult {
  id: string;
  source_id: string;
  benchmark_id: string;
  run_id: string | null;
  success: boolean;
  result_count: number;
  response_time_ms: number | null;
  duplicate_count: number;
  tested_at: string;
}

export interface BenchmarkRun {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  sources_tested: number;
  titles_tested: number;
  notes: string | null;
}

export interface ImportResponse {
  imported: number;
  skipped: number;
  errors: string[];
}

export interface SourceProfile {
  source_id: string;
  movie_score: number;
  series_score: number;
  anime_score: number;
  italian_score: number;
  german_score: number;
  avg_result_count: number;
  avg_response_ms: number | null;
  reliability_pct: number;
  duplicate_rate: number;
  benchmark_runs: number;
  last_profiled: string | null;
}

export interface RankedSource {
  id: string;
  name: string;
  url: string;
  source_type: SourceType;
  status: SourceStatus;
  score: number;
  profile: SourceProfile | null;
}

// ── Discovery ────────────────────────────────────────────────────────────────

export interface DiscoverySeed {
  id: string;
  url: string;
  label: string | null;
  seed_type: string;
  category: string | null;
  enabled: boolean;
  last_crawled: string | null;
  created_at: string;
  parent_seed_id: string | null;
  is_bred: boolean;
  breed_depth: number;
}

export interface DiscoverySeedCreate {
  url: string;
  label?: string;
  seed_type: string;
  category?: string;
  enabled?: boolean;
  parent_seed_id?: string;
  is_bred?: boolean;
  breed_depth?: number;
}

export interface DiscoveryRun {
  id: string;
  started_at: string;
  finished_at: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed';
  seeds_crawled: number;
  candidates_found: number;
  notes: string | null;
}

export interface DiscoveredSource {
  id: string;
  run_id: string | null;
  url: string;
  name: string | null;
  detected_type: string;
  detection_family: string | null;
  confidence: number | null;
  detection_reason: string | null;
  detection_method: string | null;
  status: string;
  italian_score: number | null;
  german_score: number | null;
  overall_score: number | null;
  anime_score: number | null;
  response_time_ms: number | null;
  http_status: number | null;
  notes: string | null;
  source_id: string | null;
  discovered_at: string;
  tested_at: string | null;
  benchmarked_at: string | null;
  last_benchmark_at: string | null;
  best_italian_score: number | null;
  best_german_score: number | null;
  best_overall_score: number | null;
  reject_reason: string | null;
}

export interface DiscoveryBenchmarkResult {
  id: string;
  source_id: string;
  run_at: string;
  is_online: boolean;
  response_ms: number | null;
  total_results: number;
  italian_results: number;
  german_results: number;
  english_results: number;
  anime_results: number;
  dubbed_results: number;
  results_4k: number;
  results_1080p: number;
  results_720p: number;
  has_debrid_links: boolean;
  italian_score: number;
  german_score: number;
  anime_score: number;
  overall_score: number;
  test_queries_run: string[] | null;
  raw_sample: string[] | null;
}

export interface DiscoveryRejected {
  id: number;
  url: string;
  rejection_reason: string;
  source_seed: string | null;
  discovered_at: string;
}

export interface DiscoveryStats {
  total_candidates: number;
  tested: number;
  benchmarked: number;
  approved: number;
  imported: number;
  ignored: number;
  dead: number;
  total_seeds: number;
  active_seeds: number;
  total_runs: number;
  total_rejected: number;
  auto_discovery_enabled: boolean;
  discovery_interval_hours: number;
  next_scheduled_at: string | null;
  total_bred_seeds: number;
}

export interface AppSetting {
  key: string;
  value: string;
}
