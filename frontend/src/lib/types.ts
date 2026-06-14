export type SourceType = 'torznab' | 'newznab' | 'rss' | 'manifest' | 'generic_http';
export type SourceStatus = 'unknown' | 'active' | 'degraded' | 'dead';

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
