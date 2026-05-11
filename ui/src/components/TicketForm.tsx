import type {
  UseFormRegister,
  FieldErrors,
  Control,
  Path,
  FieldValues,
} from "react-hook-form";
import { Controller } from "react-hook-form";
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
  register: UseFormRegister<T>;
  errors: FieldErrors<T>;
  control: Control<T>;
  isPending: boolean;
  submitLabel: string;
  mode: "create" | "edit";
  services: ServiceResponse[];
}

export function TicketForm<T extends FieldValues>({
  register,
  errors,
  control,
  isPending,
  submitLabel,
  mode,
  services,
}: TicketFormProps<T>) {
  return (
    <div className="flex flex-col gap-4">
      <Input {...register("title" as Path<T>)} placeholder="Title" />
      {errors.title?.message && (
        <p className="text-sm text-destructive">
          {String(errors.title.message)}
        </p>
      )}
      <Textarea
        {...register("description" as Path<T>)}
        placeholder="Description (optional)"
      />
      <Controller
        control={control}
        name={"priority" as Path<T>}
        render={({ field }) => (
          <Select value={field.value ?? ""} onValueChange={field.onChange}>
            <SelectTrigger className="w-full" aria-label="Priority">
              <SelectValue placeholder="Select priority" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="p1">P1 - Critical</SelectItem>
              <SelectItem value="p2">P2 - High</SelectItem>
              <SelectItem value="p3">P3 - Medium</SelectItem>
              <SelectItem value="p4">P4 - Low</SelectItem>
            </SelectContent>
          </Select>
        )}
      />
      {errors.priority?.message && (
        <p className="text-sm text-destructive">
          {String(errors.priority.message)}
        </p>
      )}
      {mode === "create" && (
        <Controller
          control={control}
          name={"service_id" as Path<T>}
          render={({ field }) => (
            <Select value={field.value ?? ""} onValueChange={field.onChange}>
              <SelectTrigger className="w-full" aria-label="Service">
                <SelectValue placeholder="Select service" />
              </SelectTrigger>
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
          )}
        />
      )}
      <Input {...register("assignee" as Path<T>)} placeholder="Assignee" />
      <Input {...register("reporter" as Path<T>)} placeholder="Reporter" />
      <Button type="submit" disabled={isPending}>
        {submitLabel}
      </Button>
    </div>
  );
}
