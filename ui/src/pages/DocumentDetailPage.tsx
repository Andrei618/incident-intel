import { Link, useParams } from "react-router-dom";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import { apiClient } from "@/lib/apiClient";
import { queryKey } from "@/lib/queryKeys";
import { DescriptionItem } from "@/components/DescriptionItem";
import { Badge } from "@/components/ui/badge";
import { docTypeColor } from "@/utils/colors";
import { formatTimestamp } from "@/utils/formatTimestamp";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { useServices } from "@/hooks/useServices";
import type { components } from "@/types/api";
import { Markdown } from "@/components/Markdown";

type DocumentDetailResponse = components["schemas"]["DocumentDetailResponse"];

export default function DocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const { services } = useServices();
  const {
    data: doc,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.documents.detail(documentId!),
    queryFn: () =>
      apiClient.get<DocumentDetailResponse>(`/api/v1/documents/${documentId}`),
    enabled: !!documentId,
  });
  const serviceName = services?.find((s) => s.id === doc?.service_id)?.name;

  if (!documentId) return <p>Invalid URL</p>;
  if (isLoading)
    return (
      <Card>
        <CardHeader>
          <LoadingSkeleton className="h-6 w-1/2" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3">
            <LoadingSkeleton className="h-4 w-1/3" />
            <LoadingSkeleton className="h-4 w-1/3" />
            <LoadingSkeleton className="h-4 w-1/3" />
            <LoadingSkeleton className="h-4 w-1/3" />
          </div>
        </CardContent>
      </Card>
    );
  if (error) return <p>Error: {error.message}</p>;
  if (!doc) return null;

  return (
    <div className={CONTENT_MAX_WIDTH}>
        <div className="mb-4">
           <Link to="/documents">← Back to documents</Link> 
        </div>
      
      <Card>
        <CardHeader>
          <CardTitle>{doc.title}</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="flex flex-col gap-3">
            <DescriptionItem
              label="Document type"
              value={
                <Badge variant="outline" className={docTypeColor(doc.doc_type)}>
                  {doc.doc_type}
                </Badge>
              }
            />
            <DescriptionItem label="Service" value={serviceName} />

            <DescriptionItem
              label="Created"
              value={formatTimestamp(doc.created_at)}
            />
            <DescriptionItem
              label="Updated"
              value={doc.updated_at && formatTimestamp(doc.updated_at)}
            />
          </dl>
          <div className="mt-6">
            <Markdown>{doc.content}</Markdown>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
