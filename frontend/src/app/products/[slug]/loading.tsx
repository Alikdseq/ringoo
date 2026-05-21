export default function ProductLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl animate-pulse px-4 py-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="aspect-square rounded-2xl bg-zinc-100" />
        <div className="space-y-4 rounded-[32px] border border-border p-8">
          <div className="h-10 w-3/4 rounded bg-zinc-100" />
          <div className="h-6 w-1/2 rounded bg-zinc-100" />
          <div className="h-14 w-1/3 rounded bg-zinc-100" />
        </div>
      </div>
    </div>
  );
}
