const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600",
  in_review: "bg-yellow-100 text-yellow-700",
  enriched: "bg-green-100 text-green-700",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Ожидает",
  in_review: "На ревью",
  enriched: "Обогащён",
};

export default function EnrichmentBadge({ status }: { status: string }) {
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[status] ?? STATUS_STYLES.pending}`}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}
