import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { apiClient } from "@/lib/apiClient";
import { useState } from "react";
import { Plus } from "lucide-react";
import type { components } from "@/types/api";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";

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
import { PaginationControls } from "@/components/PaginationControls";
import { ticketListSchema } from "@/schemas/api/ticket";

const LIMIT = 20;

type TicketStatus = components["schemas"]["TicketStatus"];
type StatusFilter = TicketStatus | "all";

type TicketPriority = components["schemas"]["TicketPriority"];
type PriorityFilter = TicketPriority | "all";

export default function TicketsPage() {
  const [status, setStatus] = useState<StatusFilter>("all");
  const [priority, setPriority] = useState<PriorityFilter>("all");
  const [searchParams, setSearchParam] = useSearchParams();
  const offset = Number(searchParams.get("offset") ?? "0");
  const params = new URLSearchParams();
  if (status !== "all") params.set("status", status);
  if (priority !== "all") params.set("priority", priority);
  params.set("limit", String(LIMIT));
  params.set("offset", String(offset));
  const url = `/api/v1/tickets?${params}`;

  const {
    data: tickets,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.tickets.list({ status, priority, offset }),
    queryFn: () => apiClient.get(url, ticketListSchema),
  });

  return (
    <div className={CONTENT_MAX_WIDTH}>
      <div className="flex flex-wrap gap-4 mb-4">
        <label className="text-sm flex flex-col gap-1">
          Status
          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value as StatusFilter);
              setSearchParam({});
            }}
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
            onValueChange={(value) => {
              setPriority(value as PriorityFilter);
              setSearchParam({});
            }}
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
          <Link to="new">
            <Plus className="mr-2 h-4 w-4" />
            New Ticket
          </Link>
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
      {error && <p className="text-destructive">Error: {error.message}</p>}
      {tickets && tickets.total > 0 && (
        <p className="text-sm text-muted-foreground mb-3">
          Found {tickets.total} {tickets.total === 1 ? "ticket" : "tickets"}
        </p>
      )}
      {tickets && tickets.items.length > 0 && (
        <>
          <div className="space-y-3">
            {tickets.items.map((item) => (
              <TicketCard key={item.id} ticket={item} />
            ))}
          </div>
          <div className="flex items-center gap-2 mt-4">
            <PaginationControls
              total={tickets.total}
              limit={LIMIT}
              offset={offset}
            />
          </div>
        </>
      )}
      {tickets && tickets.items.length === 0 && (
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
