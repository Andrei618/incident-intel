import type { ReactNode } from "react";

interface DescriptionItemProps {
  label: string;
  value: ReactNode;
}

export function DescriptionItem({ label, value }: DescriptionItemProps) {
    if (value === null || value === undefined) return null;
    return (
        <div>
            <dt className="text-sm text-muted-foreground">{label}</dt>
            <dd className="text-sm font-medium">{value}</dd>
        </div>
    )
}
