// Configuration types
export interface AgentConfig {
  mode: "local" | "remote";
  agent_name: string;
  agent_arn?: string;
  region?: string;
  session_id: string;
  auth_method: "iam" | "oauth" | "none";
  memory_id?: string;
}

// Chat message types
export interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: Date;
}

// Memory types
export type MemoryType = "short-term" | "short-term-and-long-term";
export type StrategyType =
  | "semantic"
  | "summary"
  | "user_preference"
  | "custom";
export type StrategyStatus = "active" | "creating" | "failed";

export interface MemoryStrategy {
  strategyId: string;
  name: string;
  type: StrategyType;
  status: StrategyStatus;
  description?: string;
  namespaces?: string[];
  configuration?: {
    extraction?: Record<string, unknown>;
    consolidation?: Record<string, unknown>;
  };
}

export interface MemoryResource {
  memory_id: string;
  name: string;
  status: string;
  event_expiry_days: number;
  memory_type: MemoryType;
  strategies: MemoryStrategy[];
}

// API request/response types
export interface InvokeRequest {
  message: string;
  session_id: string;
  bearer_token?: string;
  user_id?: string;
}

export interface InvokeResponse {
  response: string | Record<string, unknown>;
  session_id: string;
  timestamp: string;
}

export interface NewSessionResponse {
  session_id: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
