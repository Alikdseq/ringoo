import type { Metadata } from 'next';
import dynamic from 'next/dynamic';
import { HomeSvoiDialogueGate } from '@/components/home/HomeSvoiDialogueGate';
import { PromoFomoCarousel } from '@/components/home/PromoFomoCarousel';
import { HeroWithCategories } from '@/components/home/HeroWithCategories';
import { TodaysProductsCarousel } from '@/components/home/TodaysProductsCarousel';
import { InstallmentZeroSection } from '@/components/home/InstallmentZeroSection';
import { NearbyStoresSection } from '@/components/home/NearbyStoresSection';
import { PopularNowSection } from '@/components/home/PopularNowSection';
import { JsonLd, buildPageMetadata, organizationJsonLd, webSiteJsonLd } from '@/lib/seo';
import { SEO_GEO_CITY } from '@/lib/seo/constants';
import { fetchProductsServer } from '@/lib/api/services/products.service';

const VideoReviewsSection = dynamic(
  () =>
    import('@/components/home/VideoReviewsSection').then(m => ({
      default: m.VideoReviewsSection,
    })),
  { loading: () => <div className="min-h-[200px] animate-pulse rounded-2xl bg-zinc-100" /> }
);

const GiftTilesSection = dynamic(
  () =>
    import('@/components/home/GiftTilesSection').then(m => ({
      default: m.GiftTilesSection,
    })),
  { loading: () => <div className="min-h-[120px] animate-pulse rounded-2xl bg-zinc-100" /> }
);

const BenefitsSection = dynamic(
  () =>
    import('@/components/home/BenefitsSection').then(m => ({
      default: m.BenefitsSection,
    })),
  { loading: () => <div className="min-h-[160px] animate-pulse rounded-2xl bg-zinc-100" /> }
);

const SubscribeDealsSection = dynamic(
  () =>
    import('@/components/home/SubscribeDealsSection').then(m => ({
      default: m.SubscribeDealsSection,
    })),
  { loading: () => <div className="min-h-[120px] animate-pulse rounded-2xl bg-zinc-100" /> }
);

export const metadata: Metadata = buildPageMetadata({
  title: `Ringoo — магазин электроники в ${SEO_GEO_CITY} | iPhone, Samsung, доставка`,
  description:
    'Сеть Ringoo в Северной Осетии: смартфоны Apple и Samsung, аксессуары. Самовывоз сегодня, рассрочка 0%, доставка по Владикавказу и РФ.',
  path: '/',
});

const HOME_PRODUCT_FILTERS = {
  page_size: 8,
  page: 1,
  ordering: 'created_at' as const,
};

export default async function Home() {
  const [samsungPage, iphonePage] = await Promise.all([
    fetchProductsServer({ ...HOME_PRODUCT_FILTERS, category: 'samsung' }),
    fetchProductsServer({ ...HOME_PRODUCT_FILTERS, category: 'iphone' }),
  ]);

  return (
    <>
      <JsonLd data={[organizationJsonLd(), webSiteJsonLd()]} />
      <HomeSvoiDialogueGate />
      <HeroWithCategories />
      <PromoFomoCarousel />
      <TodaysProductsCarousel initialIphone={iphonePage} initialAndroid={samsungPage} />
      <InstallmentZeroSection />
      <NearbyStoresSection />
      <PopularNowSection initialSamsung={samsungPage} initialIphone={iphonePage} />
      <VideoReviewsSection />
      <GiftTilesSection />
      <BenefitsSection />
      <SubscribeDealsSection />
    </>
  );
}
