import { useParams } from "react-router-dom";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import { DescriptionItem } from "@/components/DescriptionItem";
import { Badge } from "@/components/ui/badge";
import { statusColor, priorityColor } from "@/utils/colors";
import { formatTimestamp } from "@/utils/formatTimestamp";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import { useTicket } from "@/hooks/useTicket";
import { useServices } from "@/hooks/useServices";
import { nextStates, TRANSITION_LABELS } from "@/lib/ticketTransitions";
import { useTicketTransition } from "@/hooks/useTicketMutations";
import { DeleteConfirmDialog } from "@/components/DeleteConfirmDialog";
import { useTicketDelete } from "@/hooks/useTicketMutations";

export default function TicketDetailPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { ticket, isLoading, error } = useTicket(ticketId!);
  const { services } = useServices();
  const serviceName =
    services?.find((s) => s.id === ticket?.service_id)?.name ??
    ticket?.service_id;
  const { mutate: transition, isPending: isTransitioning } =
    useTicketTransition(ticketId!);
  const { mutate: deleteTicket, isPending: isDeleting } = useTicketDelete(
    ticketId!
  );

  if (!ticketId) return <p>Invalid URL</p>;

  if (isLoading)
    return (
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
    );
  if (error) return <p>Error: {error.message}</p>;
  if (!ticket) return null;

  return (
    <div className={CONTENT_MAX_WIDTH}>
      <div className="flex items-center justify-between mb-6">
        <Link to="/tickets">← Back to tickets</Link>
        <div className="flex gap-2">
          {ticket.status !== "closed" && (
            <Button variant="outline" asChild>
              <Link to={`/tickets/${ticketId}/edit`}>Edit</Link>
            </Button>
          )}
          <DeleteConfirmDialog
            title="Delete ticket"
            description="This action cannot be undone."
            onConfirm={() => deleteTicket()}
            isPending={isDeleting}
          />
        </div>
      </div>

      <div>
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <CardTitle>{ticket.title}</CardTitle>
              <div className="flex gap-2 flex-wrap">
                {nextStates(ticket.status).map((nextStatus) => (
                  <Button
                    key={nextStatus}
                    size="sm"
                    variant="outline"
                    onClick={() => transition({ status: nextStatus })}
                    disabled={isTransitioning}
                  >
                    {TRANSITION_LABELS[nextStatus]}
                  </Button>
                ))}
                {nextStates(ticket.status).length === 0 && (
                  <span className="text-sm text-muted-foreground">
                    Closed — terminal
                  </span>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <dl className="flex flex-col gap-3">
              <DescriptionItem label="Description" value={ticket.description} />

              <DescriptionItem
                label="Status"
                value={
                  <Badge
                    variant="outline"
                    className={statusColor(ticket.status)}
                  >
                    {ticket.status}
                  </Badge>
                }
              />

              <DescriptionItem
                label="Priority"
                value={
                  <Badge
                    variant="outline"
                    className={priorityColor(ticket.priority)}
                  >
                    {ticket.priority}
                  </Badge>
                }
              />

              <DescriptionItem
                label="Created"
                value={formatTimestamp(ticket.created_at)}
              />

              <DescriptionItem
                label="Updated"
                value={ticket.updated_at && formatTimestamp(ticket.updated_at)}
              />

              <DescriptionItem
                label="Started"
                value={ticket.started_at && formatTimestamp(ticket.started_at)}
              />

              <DescriptionItem
                label="Resolved"
                value={
                  ticket.resolved_at && formatTimestamp(ticket.resolved_at)
                }
              />

              <DescriptionItem label="Service" value={serviceName} />
              <DescriptionItem label="Assignee" value={ticket.assignee} />
              <DescriptionItem label="Reporter" value={ticket.reporter} />
            </dl>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
