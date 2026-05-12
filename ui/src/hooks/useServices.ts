import { apiClient } from "@/lib/apiClient";
import { queryKey } from "@/lib/queryKeys";
import type { components } from "@/types/api";
import { useQuery } from "@tanstack/react-query";

type ServiceResponse = components["schemas"]["ServiceResponse"];

export function useServices() {
  const {
    data: services,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.services.all(),
    queryFn: () => apiClient.get<ServiceResponse[]>("/api/v1/services"),
  });
  return { services, isLoading, error };
}
