import type { Metadata } from 'next';
import { StaffDetailContent } from '@/app/staff/[slug]/StaffDetailContent';

interface PageProps {
  params: Promise<{ slug: string }>;
}

export const metadata: Metadata = {
  title: 'Консультант | Ringoo',
};

export default async function StaffBySlugPage({ params }: PageProps) {
  const { slug } = await params;
  return <StaffDetailContent slug={decodeURIComponent(slug)} />;
}
