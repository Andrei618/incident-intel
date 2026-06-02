import type { components } from "@/types/api";

// Starting thresholds — educated guesses based on each method's score scale.
// Calibrate against real queries once II-064 expands the seed corpus.
// Vector scores < 0.3 are filtered server-side (MIN_VECTOR_SIMILARITY).

export type SearchMethod = components["schemas"]["Method"];
type SearchRelevance = "strong" | "medium" | "weak";

const THRESHOLDS = {
  vector: { strong: 0.5, medium: 0.31 },  // Weak: 0.3–0.31 (BE cuts < 0.3)
  keyword: { strong: 0.1, medium: 0.03 },
  hybrid: { strong: 0.02, medium: 0.01 },
};

export function relevanceBand(
  score: number,
  method: SearchMethod
): SearchRelevance {
  const t = THRESHOLDS[method];
  if (score >= t.strong) return "strong";
  if (score >= t.medium) return "medium";
  return "weak";
}

export function relevanceColor(band: SearchRelevance) {
  switch (band) {
    case "strong":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
    case "medium":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200";
    case "weak":
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
  }
}
