import type { Control, Path, FieldValues } from "react-hook-form";
import {
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { components } from "@/types/api";

type ServiceResponse = components["schemas"]["ServiceResponse"];

interface TicketFormProps<T extends FieldValues> {
  control: Control<T>;
  isPending: boolean;
  submitLabel: string;
  mode: "create" | "edit";
  services: ServiceResponse[];
}

export function TicketForm<T extends FieldValues>({
  control,
  isPending,
  submitLabel,
  mode,
  services,
}: TicketFormProps<T>) {
  return (
    <div className="flex flex-col gap-4">
      <FormField
        control={control}
        name={"title" as Path<T>}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Title</FormLabel>
            <FormControl>
              <Input placeholder="Title" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name={"description" as Path<T>}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Description</FormLabel>
            <FormControl>
              <Textarea placeholder="Description (optional)" {...field} />
            </FormControl>
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name={"priority" as Path<T>}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Priority</FormLabel>
            <Select value={field.value ?? ""} onValueChange={field.onChange}>
              <FormControl>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
              </FormControl>
              <SelectContent>
                <SelectItem value="p1">P1 - Critical</SelectItem>
                <SelectItem value="p2">P2 - High</SelectItem>
                <SelectItem value="p3">P3 - Medium</SelectItem>
                <SelectItem value="p4">P4 - Low</SelectItem>
              </SelectContent>
            </Select>
            <FormMessage />
          </FormItem>
        )}
      />

      {mode === "create" && (
        <FormField
          control={control}
          name={"service_id" as Path<T>}
          render={({ field }) => (
            <FormItem>
              <FormLabel>Service</FormLabel>
              <Select value={field.value ?? ""} onValueChange={field.onChange}>
                <FormControl>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select service" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  {services.length === 0 ? (
                    <div className="px-2 py-1.5 text-sm text-muted-foreground">
                      No services available
                    </div>
                  ) : (
                    services.map((service) => (
                      <SelectItem key={service.id} value={service.id}>
                        {service.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
      )}

      <FormField
        control={control}
        name={"assignee" as Path<T>}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Assignee</FormLabel>
            <FormControl>
              <Input placeholder="Assignee" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <FormField
        control={control}
        name={"reporter" as Path<T>}
        render={({ field }) => (
          <FormItem>
            <FormLabel>Reporter</FormLabel>
            <FormControl>
              <Input placeholder="Reporter" {...field} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <Button type="submit" disabled={isPending} className="ml-auto">
        {submitLabel}
      </Button>
    </div>
  );
}
