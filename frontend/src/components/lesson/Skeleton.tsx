interface SkeletonProps {
  className?: string;
}

/** Shimmering placeholder block used while enrichment content loads. */
export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-md bg-surface2 ${className}`}
    />
  );
}

export function CardSkeleton({ lines = 3, title }: { lines?: number; title?: string }) {
  return (
    <div className="card p-5" role="status" aria-label={title ?? "Loading"}>
      <Skeleton className="mb-4 h-3 w-32" />
      <div className="space-y-2.5">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className={`h-3.5 ${i === lines - 1 ? "w-2/3" : "w-full"}`} />
        ))}
      </div>
    </div>
  );
}
