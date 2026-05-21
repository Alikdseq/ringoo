import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

import { authCookiesMode } from '@/lib/auth-mode';

const ACCESS_COOKIE =
  process.env.NEXT_PUBLIC_JWT_COOKIE_ACCESS_NAME ?? 'ringoo_access';
const REFRESH_COOKIE =
  process.env.NEXT_PUBLIC_JWT_COOKIE_REFRESH_NAME ?? 'ringoo_refresh';

function hasAuthCookie(req: NextRequest): boolean {
  const a = req.cookies.get(ACCESS_COOKIE)?.value;
  const r = req.cookies.get(REFRESH_COOKIE)?.value;
  return Boolean((a && a.length > 0) || (r && r.length > 0));
}

function isOrdersPublicPath(pathname: string): boolean {
  if (pathname === '/orders/success' || pathname.startsWith('/orders/success/')) {
    return true;
  }
  return /^\/orders\/[^/]+\/success\/?$/.test(pathname);
}

export function middleware(request: NextRequest) {
  if (!authCookiesMode()) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;

  if (pathname.startsWith('/admin/login')) {
    return NextResponse.next();
  }

  if (isOrdersPublicPath(pathname)) {
    return NextResponse.next();
  }

  const nextArg = pathname + request.nextUrl.search;

  if (pathname.startsWith('/profile')) {
    if (!hasAuthCookie(request)) {
      const url = request.nextUrl.clone();
      url.pathname = '/login';
      url.search = `?next=${encodeURIComponent(nextArg)}`;
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  if (pathname === '/orders' || pathname.startsWith('/orders/')) {
    if (!hasAuthCookie(request)) {
      const url = request.nextUrl.clone();
      url.pathname = '/login';
      url.search = `?next=${encodeURIComponent(nextArg)}`;
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  if (pathname.startsWith('/admin')) {
    if (!hasAuthCookie(request)) {
      const url = request.nextUrl.clone();
      url.pathname = '/admin/login';
      url.search = `?next=${encodeURIComponent(pathname)}`;
      return NextResponse.redirect(url);
    }
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/profile/:path*', '/orders/:path*', '/orders', '/admin/:path*', '/admin'],
};
