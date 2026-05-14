import { Link } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { docTypeColor } from "@/utils/colors";
import { formatTimestamp } from "@/utils/formatTimestamp";
import type { components } from "@/types/api";
import { Badge } from "@/components/ui/badge";

type DocumentResponse = components["schemas"]["DocumentResponse"];
interface DocumentCardProps {
  doc: DocumentResponse;
}

export function DocumentCard({ doc }: DocumentCardProps) {
  return (
    <Link
      to={`/documents/${doc.id}`}
      className="block no-underline text-current"
      aria-label={`Open doc: ${doc.title}`}
    >
      <Card className="hover:bg-accent/50 transition-colors">
        <CardHeader>
          <CardTitle>{doc.title}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <Badge variant="outline" className={docTypeColor(doc.doc_type)}>
            {doc.doc_type.toUpperCase()}
          </Badge>
          <span>{formatTimestamp(doc.created_at)}</span>
        </CardContent>
      </Card>
    </Link>
  );
}
