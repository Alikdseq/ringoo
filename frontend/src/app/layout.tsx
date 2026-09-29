import type { Metadata, Viewport } from 'next';
import { cookies } from 'next/headers';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { QueryProvider } from '@/lib/providers/QueryProvider';
import { CartFlyProvider } from '@/lib/providers/CartFlyProvider';
import { UiModeProvider } from '@/lib/providers/UiModeProvider';
import { ShellSelector } from '@/components/layout/ShellSelector';
import { RingikLauncher } from '@/components/ringik/RingikLauncher';
import { UI_MODE_COOKIE_NAME, type UiMode } from '@/lib/ui-mode/types';
import { UI_MODE_SVOI_ENABLED } from '@/lib/ui-mode/featureFlags';
import { isUiMode } from '@/lib/ui-mode/storage';
import { buildRootMetadata } from '@/lib/seo';
import { LegalAnalyticsProviders } from '@/components/legal/LegalAnalyticsProviders';
import { fetchCategoriesServer } from '@/lib/api/services/products.service';

// Cyrillic UI: без subset cyrillic preload Geist не используется для глифов → предупреждение Chrome.
const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin', 'cyrillic'],
  display: 'swap',
  preload: false,
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin', 'cyrillic'],
  display: 'swap',
  preload: false, // редко above-the-fold — меньше шума «preloaded but not used»
});

export const metadata: Metadata = buildRootMetadata();

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cookieStore = await cookies();
  const raw = cookieStore.get(UI_MODE_COOKIE_NAME)?.value;
  const initialUiMode: UiMode =
    UI_MODE_SVOI_ENABLED && isUiMode(raw) ? raw : 'official';

  const uiModeBootstrap = UI_MODE_SVOI_ENABLED
    ? `(function(){try{var c=document.cookie.match(/(?:^|; )ringoo_ui_mode=(official|svoi)(?:;|$)/);var v=c?c[1]:(typeof localStorage!=='undefined'?localStorage.getItem('ringoo_ui_mode'):null);if(v==='svoi'||v==='official'){document.documentElement.setAttribute('data-ui-mode',v);}else{document.documentElement.setAttribute('data-ui-mode','official');}}catch(e){document.documentElement.setAttribute('data-ui-mode','official');}})();`
    : `(function(){try{document.documentElement.setAttribute('data-ui-mode','official');}catch(e){document.documentElement.setAttribute('data-ui-mode','official');}})();`;

  const bodyModeClass = initialUiMode === 'svoi' ? 'mode-svoi' : 'mode-official';
  const initialCategories = await fetchCategoriesServer();

  return (
    <html lang="ru" suppressHydrationWarning data-ui-mode={initialUiMode}>
      <head>
        <script
          id="ringoo-ui-mode-bootstrap"
          // beforeInteractive: без next/script в дереве React — нет предупреждения о script в клиентском рендере
          dangerouslySetInnerHTML={{ __html: uiModeBootstrap }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} relative ${bodyModeClass} antialiased overflow-x-hidden`}
      >
        <QueryProvider>
          <CartFlyProvider>
            <UiModeProvider initialMode={initialUiMode}>
              <ShellSelector initialCategories={initialCategories}>
                {children}
                <RingikLauncher />
                <LegalAnalyticsProviders />
              </ShellSelector>
            </UiModeProvider>
          </CartFlyProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
