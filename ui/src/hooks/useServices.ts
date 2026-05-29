import { apiClient } from "@/lib/apiClient";
import { queryKey } from "@/lib/queryKeys";
import { useQuery } from "@tanstack/react-query";
import { serviceListSchema } from "@/schemas/api/service";

export function useServices() {
  const {
    data: services,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.services.all(),
    queryFn: () => apiClient.get("/api/v1/services", serviceListSchema),
  });
  return { services, isLoading, error };
}
