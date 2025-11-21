/**
 * API client for communicating with the AgentCore UI backend.
 *
 * This client handles all HTTP requests to the FastAPI backend,
 * including agent invocation, configuration retrieval, session management,
 * and memory inspection.
 */

import type {
  AgentConfig,
  InvokeRequest,
  InvokeResponse,
  NewSessionResponse,
  MemoryResource,
} from "../types";

// Use environment variable for API base URL in dev mode, empty string for production
// In production, the API is served from the same origin
const API_BASE_URL = import.meta.env.DEV
  ? import.meta.env.VITE_API_BASE_URL || ""
  : "";

/**
 * API client class for making requests to the backend.
 */
class ApiClient {
  /**
   * Generic request method that handles all HTTP requests.
   *
   * @param endpoint - API endpoint path (e.g., "/api/config")
   * @param options - Fetch options (method, body, headers, etc.)
   * @returns Promise resolving to the typed response data
   * @throws Error if the request fails or returns a non-OK status
   */
  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      console.log({ error });
      throw new Error(error.detail.message || "An error occurred");
    }

    return response.json();
  }

  /**
   * Fetch agent configuration from the backend.
   *
   * @returns Promise resolving to AgentConfig with mode, agent details, and session ID
   */
  async getConfig(): Promise<AgentConfig> {
    return this.request<AgentConfig>("/api/config");
  }

  /**
   * Invoke the agent with a user message.
   *
   * @param data - InvokeRequest containing message, session_id, and optional bearer_token
   * @returns Promise resolving to InvokeResponse with agent response and timestamp
   */
  async invoke(data: InvokeRequest): Promise<InvokeResponse> {
    return this.request<InvokeResponse>("/api/invoke", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Create a new conversation session.
   *
   * @returns Promise resolving to NewSessionResponse with new session_id
   */
  async createNewSession(): Promise<NewSessionResponse> {
    return this.request<NewSessionResponse>("/api/session/new", {
      method: "POST",
    });
  }

  /**
   * Fetch memory resource details including all strategies.
   *
   * @returns Promise resolving to MemoryResource with memory details and strategies
   */
  async getMemory(): Promise<MemoryResource> {
    return this.request<MemoryResource>("/api/memory");
  }
}

/**
 * Singleton API client instance for use throughout the application.
 */
export const apiClient = new ApiClient();
