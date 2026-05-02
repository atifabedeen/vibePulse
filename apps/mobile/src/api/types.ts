// TS mirror of services/api/app/schemas/*.py.
// Keep these in sync with the Python schemas — they're the wire contract.

// --- user / auth ---------------------------------------------------------

export interface UserOut {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  created_at: string; // ISO datetime
  updated_at: string;
}

export interface UserUpdate {
  display_name?: string | null;
  avatar_url?: string | null;
}

export interface RegisterIn {
  email: string;
  password: string;
  display_name: string;
  avatar_url?: string | null;
}

export interface LoginIn {
  email: string;
  password: string;
}

export interface RefreshIn {
  refresh_token: string;
}

export interface AccessTokenOut {
  access_token: string;
  token_type: string;
}

export interface TokenPair {
  user: UserOut;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type MeOut = UserOut;

// --- mission -------------------------------------------------------------

export interface LatLng {
  lat: number;
  lng: number;
}

export interface MissionCreate {
  title: string;
  description?: string | null;
  location: LatLng;
  search_radius_m?: number;
  scheduled_for?: string | null;
}

export interface MissionUpdate {
  title?: string | null;
  description?: string | null;
  location?: LatLng | null;
  search_radius_m?: number | null;
  scheduled_for?: string | null;
  status?: string | null;
}

export type MissionStatus =
  | 'draft'
  | 'collecting_prefs'
  | 'recommending'
  | 'voting'
  | 'finalized'
  | 'cancelled';

export interface MissionOut {
  id: string;
  creator_id: string;
  title: string;
  description: string | null;
  status: string;
  location: LatLng;
  search_radius_m: number;
  scheduled_for: string | null;
  winner_place_id: string | null;
  backup_place_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface MissionMemberOut {
  user_id: string;
  role: string; // 'owner' | 'member'
  joined_at: string;
}

export interface MissionDetailOut extends MissionOut {
  members: MissionMemberOut[];
}

export interface MissionListOut {
  items: MissionOut[];
  next_cursor: string | null;
}

export interface InviteCreate {
  expires_in_hours?: number;
  max_uses?: number;
}

export interface InviteOut {
  id: string;
  mission_id: string;
  token: string;
  expires_at: string;
  max_uses: number;
  uses: number;
  created_at: string;
}

export interface RedeemIn {
  token: string;
}

export interface ReplanIn {
  reason?: string | null;
  overrides?: Record<string, unknown> | null;
}

export interface ReplanOut {
  agent_run_id: string;
}

// --- preference ----------------------------------------------------------

export interface PreferencePayload {
  budget_max_cents?: number | null;
  distance_tolerance_m?: number | null;
  cuisines_like?: string[];
  cuisines_dislike?: string[];
  dietary_restrictions?: string[];
  vibe?: string | null;
  noise_tolerance?: number | null;
  seating_preference?: string | null;
  urgency?: number | null;
  hunger_level?: number | null;
  raw_comment?: string | null;
}

export interface PreferenceParseIn {
  raw_comment: string;
}

export interface PreferenceOut {
  mission_id: string;
  user_id: string;
  budget_max_cents: number | null;
  distance_tolerance_m: number | null;
  cuisines_like: string[];
  cuisines_dislike: string[];
  dietary_restrictions: string[];
  vibe: string | null;
  noise_tolerance: number | null;
  seating_preference: string | null;
  urgency: number | null;
  hunger_level: number | null;
  raw_comment: string | null;
  parsed_at: string | null;
  updated_at: string;
}

// --- place ---------------------------------------------------------------

export interface PlaceOut {
  id: string;
  google_place_id: string;
  name: string;
  address: string | null;
  lat: number;
  lng: number;
  price_level: number | null;
  rating: number | null;
  user_rating_ct: number | null;
  cuisines: string[];
  fetched_at: string;
  expires_at: string;
}

export interface PlaceDetail extends PlaceOut {
  raw_blob: Record<string, unknown>;
}

export interface PlaceRefreshOut {
  agent_run_id: string;
}

// --- ranking -------------------------------------------------------------

export interface RankingItem {
  id: string;
  mission_id: string;
  place_id: string;
  agent_run_id: string;
  rank: number;
  score: number;
  // Reasons shape is open-ended on the server. The recommend graph emits
  // `pros` / `cons` arrays today; we read them defensively.
  reasons: {
    pros?: string[];
    cons?: string[];
    [k: string]: unknown;
  };
  created_at: string;
}

export interface RankingBatch {
  agent_run_id: string | null;
  items: RankingItem[];
}

// --- vote ----------------------------------------------------------------

export interface VotePayload {
  place_id: string;
  weight: 1 | -1;
}

export interface VoteOut {
  mission_id: string;
  user_id: string;
  place_id: string;
  weight: number;
  created_at: string;
}

export interface VoteCounts {
  up: number;
  veto: number;
}

export interface VoteTally {
  tally: Record<string, VoteCounts>;
}

export interface FinalizeOut {
  winner: PlaceOut | null;
  backup: PlaceOut | null;
}

// --- agents --------------------------------------------------------------

export type AgentRunStatus =
  | 'pending'
  | 'running'
  | 'interrupted'
  | 'completed'
  | 'failed';

export interface AgentRunOut {
  id: string;
  mission_id: string;
  graph_name: string;
  status: string;
  trigger: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
  started_at: string;
  finished_at: string | null;
  total_tokens: number | null;
  total_cost_usd: number | null;
}

export interface AgentRunStepOut {
  id: string;
  agent_run_id: string;
  node_name: string;
  status: string;
  input: Record<string, unknown> | null;
  output: Record<string, unknown> | null;
  tool_calls: unknown[] | null;
  error: string | null;
  latency_ms: number | null;
  started_at: string;
  finished_at: string | null;
}

export interface AgentRunDetail extends AgentRunOut {
  steps: AgentRunStepOut[];
}

export interface AgentRejectIn {
  reason: string;
  overrides?: Record<string, unknown> | null;
}

export interface AgentResumeOut {
  agent_run_id: string;
  status: string;
}

// --- error ---------------------------------------------------------------

/** RFC 7807 problem+json shape — sec 7. */
export interface ProblemDetail {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  // FastAPI default error shape uses { detail: string | object }.
  [k: string]: unknown;
}
