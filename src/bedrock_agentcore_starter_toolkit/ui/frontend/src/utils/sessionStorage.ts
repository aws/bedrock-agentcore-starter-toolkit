/**
 * Session storage utilities for persisting session ID across page refreshes.
 *
 * The session ID is stored in browser sessionStorage (not localStorage) so it
 * persists across page refreshes but is cleared when the browser tab is closed.
 */

const SESSION_ID_KEY = "agentcore_session_id";

export const sessionStorage = {
  /**
   * Retrieve the stored session ID from browser sessionStorage.
   *
   * @returns The session ID string, or null if not found or on error
   */
  getSessionId(): string | null {
    try {
      return window.sessionStorage.getItem(SESSION_ID_KEY);
    } catch (error) {
      console.error("Failed to get session ID from storage:", error);
      return null;
    }
  },

  /**
   * Save a session ID to browser sessionStorage.
   *
   * @param sessionId - The session ID to store
   */
  setSessionId(sessionId: string): void {
    try {
      window.sessionStorage.setItem(SESSION_ID_KEY, sessionId);
    } catch (error) {
      console.error("Failed to save session ID to storage:", error);
    }
  },

  /**
   * Remove the session ID from browser sessionStorage.
   * Called when starting a new conversation.
   */
  clearSessionId(): void {
    try {
      window.sessionStorage.removeItem(SESSION_ID_KEY);
    } catch (error) {
      console.error("Failed to clear session ID from storage:", error);
    }
  },
};
