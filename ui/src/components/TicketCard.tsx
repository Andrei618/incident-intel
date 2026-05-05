import { Link } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { statusColor, priorityColor } from "@/utils/colors";
import { formatTimestamp } from "@/utils/formatTimestamp";
import type { components } from "@/types/api";

type TicketResponse = components["schemas"]["TicketResponse"];
interface TicketCardProps {
  ticket: TicketResponse;
}

export function TicketCard({ ticket }: TicketCardProps) {
  return (
    <Link
      to={`/tickets/${ticket.id}`}
      className="block no-underline text-current"
      aria-label={`Open ticket: ${ticket.title}`}
    >
      <Card className="hover:bg-accent/50 transition-colors">
        <CardHeader>
          <CardTitle>{ticket.title}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <Badge variant="outline" className={statusColor(ticket.status)}>
            {ticket.status.replaceAll("_", " ")}
          </Badge>
          <Badge variant="outline" className={priorityColor(ticket.priority)}>
            {ticket.priority.toUpperCase()}
          </Badge>
          <span>{formatTimestamp(ticket.created_at)}</span>
        </CardContent>
      </Card>
    </Link>
  );
}
