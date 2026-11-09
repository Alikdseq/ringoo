import { NextResponse } from 'next/server';

/**
 * Лёгкая проверка готовности Next.js (без SSR каталога / внешних API).
 * Используется Docker HEALTHCHECK и оркестраторами.
 */
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export function GET() {
  return NextResponse.json(
    { status: 'ok', service: 'ringoo-frontend' },
    {
      status: 200,
      headers: {
        'Cache-Control': 'no-store',
      },
    }
  );
}
