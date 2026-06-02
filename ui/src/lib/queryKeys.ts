export const queryKey = {
  tickets: {
    all: () => ["tickets"] as const,
    list: (filters: Record<string, unknown>) =>
      ["tickets", "list", filters] as const,
    detail: (id: string) => ["tickets", id] as const,
  },
  documents: {
    all: () => ["documents"] as const,
    list: (filters: Record<string, unknown>) =>
      ["documents", "list", filters] as const,
    detail: (id: string) => ["documents", id] as const,
  },
  search: {
    results: (query: string, method: string) =>
      ["search", query, method] as const,
  },
  services: {
    all: () => ["services"] as const,
  },
  conversations: {
    all: () => ["conversations"] as const,
    detail: (id: string) => ["conversations", id] as const,
  },
} as const;
