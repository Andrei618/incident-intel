import { formatDistanceToNow, format, differenceInHours } from "date-fns"

export function formatTimestamp(iso: string): string {
  const eventDate = new Date(iso);
  const nowDate = new Date();
  const dateDifference = differenceInHours(nowDate, eventDate);

  if (dateDifference < 24) {
    return formatDistanceToNow(eventDate, {addSuffix: true})
  } else {
    return format(eventDate, "MMM d, yyyy")
  }
}