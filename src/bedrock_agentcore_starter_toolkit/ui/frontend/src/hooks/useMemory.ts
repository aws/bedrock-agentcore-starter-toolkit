import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../api/client";

/**
 * Custom hook for fetching memory resource details.
 *
 * Uses TanStack Query's useQuery to fetch and cache memory data,
 * including all configured strategies and their details.
 *
 * @returns Query object with data, loading state, and error information
 *
 * @example
 * const { data: memory, isLoading, error } = useMemory();
 */
export function useMemory() {
  return useQuery({
    queryKey: ["memory"],
    queryFn: () => apiClient.getMemory(),
    retry: 1, // Only retry once on failure
  });
}
