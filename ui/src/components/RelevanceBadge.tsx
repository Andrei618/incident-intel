import { Badge } from "@/components/ui/badge";
import {
  relevanceBand,
  relevanceColor,
  type SearchMethod,
} from "@/utils/relevance";

interface RelevanceProps {
  score: number;
  method: SearchMethod;
}

export function RelevanceBadge({ score, method }: RelevanceProps) {
  const band = relevanceBand(score, method);

  return (
    <Badge variant="outline" className={relevanceColor(band)}>
      {band[0].toUpperCase() + band.slice(1)}
    </Badge>
  );
}
