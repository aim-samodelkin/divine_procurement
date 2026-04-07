const COLOR: Record<string, string> = {
  red: "bg-red-500",
  yellow: "bg-yellow-400",
  green: "bg-green-500",
};

export default function CoverageBar({ count, status }: { count: number; status: string }) {
  const pct = Math.min(100, (count / 6) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${COLOR[status] ?? "bg-gray-400"}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-medium min-w-[1.5rem] text-right ${status === "red" ? "text-red-600" : status === "yellow" ? "text-yellow-600" : "text-green-600"}`}>
        {count}
      </span>
    </div>
  );
}
