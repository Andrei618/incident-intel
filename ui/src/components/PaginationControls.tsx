import { useSearchParams } from "react-router-dom";
import { Button } from "@/components/ui/button";

interface PaginationControlsProps {
  total: number;
  limit: number;
  offset: number;
}

export function PaginationControls({
  total,
  limit,
  offset,
}: PaginationControlsProps) {
  const [, setSearchParam] = useSearchParams();

  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  const goToPrev = () =>
    setSearchParam({ offset: String(Math.max(0, offset - limit)) });
  const goToNext = () => setSearchParam({ offset: String(offset + limit) });

  return (
    <>
      <Button
        variant="outline"
        onClick={goToPrev}
        disabled={!hasPrev}
        className={!hasPrev ? "text-muted-foreground border-muted" : ""}
      >
        Previous
      </Button>
      <Button
        variant="outline"
        onClick={goToNext}
        disabled={!hasNext}
        className={!hasNext ? "text-muted-foreground border-muted" : ""}
      >
        Next
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {Math.floor(offset / limit) + 1} of {Math.ceil(total / limit)}
      </span>
    </>
  );
}
