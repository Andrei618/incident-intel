import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/apiClient";
import type { components } from "@/types/api";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectValue,
  SelectTrigger,
} from "@/components/ui/select";
import { TicketCard } from "@/components/TicketCard";
import { queryKey } from "@/lib/queryKeys";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";
import { Plus, PlusCircle } from "lucide-react"

type TicketListResponse = components["schemas"]["TicketListResponse"];

type TicketStatus = components["schemas"]["TicketStatus"];
type StatusFilter = TicketStatus | "all";

type TicketPriority = components["schemas"]["TicketPriority"];
type PriorityFilter = TicketPriority | "all";

export default function TicketsPage() {
  const [status, setStatus] = useState<StatusFilter>("all");
  const [priority, setPriority] = useState<PriorityFilter>("all");

  const params = new URLSearchParams({ limit: "20" });
  if (status !== "all") params.set("status", status);
  if (priority !== "all") params.set("priority", priority);
  const url = `/api/v1/tickets?${params}`;

  const { data, isLoading, error } = useQuery({
    queryKey: queryKey.tickets.list({ status, priority }),
    queryFn: () => apiClient.get<TicketListResponse>(url),
  });

  return (
    <div className={CONTENT_MAX_WIDTH}>
      <div className="flex flex-wrap gap-4 mb-4">
        <label className="text-sm flex flex-col gap-1">
          Status
          <Select
            value={status}
            onValueChange={(value) => setStatus(value as StatusFilter)}
          >
            <SelectTrigger className="w-[180px]" aria-label="Filter by status">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="in_progress">In progress</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
              <SelectItem value="closed">Closed</SelectItem>
            </SelectContent>
          </Select>
        </label>
        <label className="text-sm flex flex-col gap-1">
          Priority
          <Select
            value={priority}
            onValueChange={(value) => setPriority(value as PriorityFilter)}
          >
            <SelectTrigger
              className="w-[180px]"
              aria-label="Filter by priority"
            >
              <SelectValue placeholder="All priorities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All priorities</SelectItem>
              <SelectItem value="p1">P1 - Critical</SelectItem>
              <SelectItem value="p2">P2 - High</SelectItem>
              <SelectItem value="p3">P3 - Medium</SelectItem>
              <SelectItem value="p4">P4 - Low</SelectItem>
            </SelectContent>
          </Select>
        </label>
        <Button asChild className="ml-auto">
          <Link to="new"><Plus className="mr-2 h-4 w-4" />New Ticket</Link>
        </Button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
        </div>
      )}
      {error && <p>Error: {error.message}</p>}
      {data && data.total > 0 && (
        <p className="text-sm text-muted-foreground mb-3">
          Found {data.total} {data.total === 1 ? "ticket" : "tickets"}
        </p>
        )}
      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((item) => (
            <TicketCard key={item.id} ticket={item}/>
          ))}
        </div>
      )}
      {data && data.items.length === 0 && (
        <EmptyState
          title="No tickets found"
          description={
            status !== "all" || priority !== "all"
              ? "No tickets match the current filters. Try changing the status or priority."
              : "There are no tickets to display."
          }
        />
      )}
    </div>
  );
}
