import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient } from "@/lib/apiClient";
import type { components } from "@/types/api";
import { EmptyState } from "@/components/EmptyState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { CONTENT_MAX_WIDTH } from "@/lib/constants";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectValue,
  SelectTrigger,
} from "@/components/ui/select";
import { DocumentCard } from "@/components/DocumentCard";
import { queryKey } from "@/lib/queryKeys";
import { PaginationControls } from "@/components/PaginationControls";

const LIMIT = 20;
type DocumentListResponse = components["schemas"]["DocumentListResponse"];
type DocType = components["schemas"]["DocType"];
type DocTypeFilter = DocType | "all";

export default function DocumentsPage() {
  const [docType, setDocType] = useState<DocTypeFilter>("all");
  const [searchParams, setSearchParams] = useSearchParams();
  const offset = Number(searchParams.get("offset") ?? "0");
  const params = new URLSearchParams();
  if (docType !== "all") params.set("doc_type", docType);
  params.set("limit", String(LIMIT));
  params.set("offset", String(offset));
  const url = `/api/v1/documents?${params}`;

  const {
    data: docs,
    isLoading,
    error,
  } = useQuery({
    queryKey: queryKey.documents.list({ docType, offset }),
    queryFn: () => apiClient.get<DocumentListResponse>(url),
  });

  return (
    <div className={CONTENT_MAX_WIDTH}>
      <div className="mb-4">
        <label className="text-sm flex flex-col gap-1">
          Document type
          <Select
            value={docType}
            onValueChange={(value) => {
              setDocType(value as DocTypeFilter);
              setSearchParams({});
            }}
          >
            <SelectTrigger
              className="w-[180px]"
              aria-label="Filter by Document type"
            >
              <SelectValue placeholder="All types" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              <SelectItem value="runbook">Runbook</SelectItem>
              <SelectItem value="policy">Policy</SelectItem>
              <SelectItem value="guide">Guide</SelectItem>
              <SelectItem value="faq">FAQ</SelectItem>
            </SelectContent>
          </Select>
        </label>
      </div>
      {isLoading && (
        <div className="space-y-3">
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
          <LoadingSkeleton className="h-32" />
        </div>
      )}
      {error && <p className="text-destructive">Error: {error.message}</p>}
      {docs && docs.items.length > 0 && (
        <>
          <div className="space-y-3">
            {docs.items.map((item) => (
              <DocumentCard key={item.id} doc={item} />
            ))}
          </div>
          <div className="flex items-center gap-2 mt-4">
            <PaginationControls
              total={docs.total}
              limit={LIMIT}
              offset={offset}
            />
          </div>
        </>
      )}
      {docs && docs.items.length === 0 && (
        <EmptyState
          title="No documents found"
          description={
            docType !== "all"
              ? "No documents match the current filters. Try changing the document type."
              : "There are no documents to display."
          }
        />
      )}
    </div>
  );
}
