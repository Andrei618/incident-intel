import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import type { components } from "@/types/api";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Link } from "react-router-dom";
import { Markdown } from "@/components/Markdown";

type SearchResponse = components["schemas"]["SearchResponse"];

export default function SearchPage() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [method, setMethod] = useState<"keyword" | "vector" | "hybrid">(
    "hybrid"
  );

  const params = new URLSearchParams({ q: query, limit: "10", method });
  const url = `/api/v1/search?${params}`;

  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["search", query, method],
    queryFn: () => apiClient.get<SearchResponse>(url),
    enabled: query.trim().length > 0,
  });

  function handleSearch(e: React.SyntheticEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    setQuery(input);
  }

  return (
    <div className={`${CONTENT_MAX_WIDTH}`}>
      <form onSubmit={handleSearch} className="space-y-3">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search runbooks and incident reports"
        />
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Method:</span>
          <div
            role="group"
            aria-label="Search method"
            className="flex rounded-md border overflow-hidden w-fit"
          >
            {(["keyword", "vector", "hybrid"] as const).map((m) => (
              <Button
                key={m}
                type="button"
                variant={method === m ? "default" : "outline"}
                onClick={() => setMethod(m)}
                className="rounded-none border-0"
              >
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        <Button type="submit" disabled={!input.trim()}>
          Search
        </Button>
      </form>
      <div className="mt-6">
        {!query && (
          <p className="text-muted-foreground text-sm">
            Search across your runbooks and incident reports
          </p>
        )}
        {isLoading && (
          <div className="space-y-3">
            <LoadingSkeleton className="h-32"/>
            <LoadingSkeleton className="h-32"/>
            <LoadingSkeleton className="h-32"/>
            <LoadingSkeleton className="h-32"/>
          </div>
        )}
        {error && <p>Error: {error.message}</p>}
        {data && data.total > 0 && (
          <p className="text-sm text-muted-foreground">
            Found {data.total} results
          </p>
        )}
        {data && data.items.length > 0 && (
          <div className="space-y-3">
            {data.items.map((item) => (
              <Card key={item.chunk_id}>
                <CardHeader>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                    <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      {item.document_title}
                    </CardTitle>
                    <span className="text-sm text-muted-foreground font-medium">
                      Relevance: {Math.round(item.score * 100)}%
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="rounded p-3 bg-muted/50 [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm">
                    <Markdown>
                      {expandedId === item.chunk_id
                        ? item.content
                        : item.content.slice(0, 200)}
                    </Markdown>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setExpandedId(
                          expandedId === item.chunk_id ? null : item.chunk_id
                        )
                      }
                    >
                      {expandedId === item.chunk_id ? "Show less" : "Show more"}
                    </Button>

                    <Link
                      to={`/documents/${item.document_id}`}
                      className="text-primary hover:underline text-sm font-medium"
                    >
                      View document →
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        {data && data.items.length === 0 && <p>No results for '{query}'</p>}
      </div>
    </div>
  );
}
