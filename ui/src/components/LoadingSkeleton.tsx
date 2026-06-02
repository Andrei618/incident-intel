import { cn } from "@/lib/utils";

interface LoadingSkeletonProps {
  height?: string;
  className?: string;
}

export function LoadingSkeleton({ height, className }: LoadingSkeletonProps) {
    return (
        <div className={cn("animate-pulse bg-muted rounded w-full", height, className)} />
    )
}
