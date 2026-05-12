import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import { ticketUpdateSchema, type TicketUpdate } from "@/schemas/tickets";
import { useTicketUpdate } from "@/hooks/useTicketMutations";
import { useParams } from "react-router-dom";
import { useTicket } from "@/hooks/useTicket";
import { TicketForm } from "@/components/TicketForm";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

export default function TicketEditPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const { ticket, isLoading, error } = useTicket(ticketId!);
  const form = useForm<TicketUpdate>({
    resolver: zodResolver(ticketUpdateSchema),
    values: ticket ? {
        title: ticket.title,
        description: ticket.description ?? undefined,
        priority: ticket.priority,
        assignee: ticket.assignee ?? undefined,
        reporter: ticket.reporter ?? undefined,
    } : undefined,
  });
  const { mutate, isPending } = useTicketUpdate(ticketId!);

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <p className="text-destructive">Error: {error.message}</p>;

  return (
    <div className={CONTENT_MAX_WIDTH}>
      <h1 className="text-2xl font-bold mb-6">Edit Ticket</h1>
      <form onSubmit={form.handleSubmit((data) => mutate(data))}>
        <TicketForm<TicketUpdate>
          register={form.register}
          errors={form.formState.errors}
          control={form.control}
          isPending={isPending}
          submitLabel="Save changes"
          mode="edit"
          services={[]}
        />
      </form>
    </div>
  );
}
