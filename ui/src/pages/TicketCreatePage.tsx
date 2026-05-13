import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useServices } from "@/hooks/useServices";
import { useTicketCreate } from "@/hooks/useTicketMutations";
import { ticketCreateSchema, type TicketCreate } from "@/schemas/tickets";
import { TicketForm } from "@/components/TicketForm";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import { Form } from "@/components/ui/form"

export default function TicketCreatePage() {
  const form = useForm<TicketCreate>({
    resolver: zodResolver(ticketCreateSchema),
  });
  const { services } = useServices();
  const { mutate, isPending } = useTicketCreate();

  return (
    <Form {...form}>
      <div className={CONTENT_MAX_WIDTH}>
        <h1 className="text-2xl font-bold mb-6">New Ticket</h1>
        <form onSubmit={form.handleSubmit((data) => mutate(data))}>
          <TicketForm<TicketCreate>
            control={form.control}
            isPending={isPending}
            submitLabel="Save"
            mode="create"
            services={services ?? []}
          />
        </form>
      </div>
    </Form>
  );
}
