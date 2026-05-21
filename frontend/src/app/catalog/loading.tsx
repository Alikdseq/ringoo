import { CatalogSkeleton } from '@/components/ui/CatalogSkeleton';

export default function CatalogLoading() {
  return (
    <div className="min-h-screen bg-background px-4 py-6">
      <CatalogSkeleton />
    </div>
  );
}
