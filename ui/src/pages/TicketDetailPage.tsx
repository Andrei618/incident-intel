import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import type { components } from "@/types/api";
import { apiClient } from "@/lib/apiClient";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import { DescriptionItem } from "@/components/DescriptionItem";
import { Badge } from "@/components/ui/badge";
import { statusColor, priorityColor } from "@/utils/colors";
import { formatTimestamp } from "@/utils/formatTimestamp";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { queryKey } from "@/lib/queryKeys";

type TicketResponse = components["schemas"]["TicketResponse"];

export default function TicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();

  const {
    data: ticket,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.tickets.detail(ticketId!),
    queryFn: () => apiClient.get<TicketResponse>(`/api/v1/tickets/${ticketId}`),
    enabled: !!ticketId,
  });

  if (!ticketId) return <p>Invalid URL</p>;

  return (
    <div className={CONTENT_MAX_WIDTH}>
      <Link to="/tickets">← Back to tickets</Link>
      <div>
        {isLoading && (
            <Card>
                <CardHeader>
                    <LoadingSkeleton className="h-6 w-1/2" />
                </CardHeader>
                <CardContent>
                    <div className="flex flex-col gap-3">
                        <LoadingSkeleton className="h-4 w-1/3" />
                        <LoadingSkeleton className="h-4 w-1/3" />
                        <LoadingSkeleton className="h-4 w-1/3" />
                    </div>
                </CardContent>
            </Card>
        )}
        {error && <p>Error: {error.message}</p>}
        {ticket && (
          <Card>
            <CardHeader>
              <CardTitle>{ticket.title}</CardTitle>
            </CardHeader>
            <CardContent>
                <dl className="flex flex-col gap-3">
                    <DescriptionItem label="Description" value={ticket.description} />
                    <DescriptionItem
                        label="Status"
                        value={
                            <Badge variant="outline" className={statusColor(ticket.status)}>
                                {ticket.status}
                            </Badge>
                        }
                    />
                    <DescriptionItem
                        label="Priority"
                        value={
                            <Badge variant="outline" className={priorityColor(ticket.priority)}>
                                {ticket.priority}
                            </Badge>
                        }
                    />
                    <DescriptionItem label="Created" value={formatTimestamp(ticket.created_at)} />
                    <DescriptionItem label="Updated" value={ticket.updated_at && formatTimestamp(ticket.updated_at)} />
                    <DescriptionItem label="Started" value={ticket.started_at && formatTimestamp(ticket.started_at)} />
                    <DescriptionItem label="Resolved" value={ticket.resolved_at && formatTimestamp(ticket.resolved_at)} />
                    <DescriptionItem label="Service" value={ticket.service_id} />
                </dl>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
