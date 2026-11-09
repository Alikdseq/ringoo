import { describe, it, expect, afterEach } from 'vitest';
import { getMediaUrl } from './image-url';

describe('getMediaUrl', () => {
  const keys = [
    'NEXT_PUBLIC_API_URL',
    'NEXT_PUBLIC_API_V1_URL',
    'NEXT_PUBLIC_SITE_URL',
    'NEXT_PUBLIC_APP_URL',
    'RINGOO_NGROK_DEMO',
  ] as const;
  const originalEnv: Record<string, string | undefined> = {};

  afterEach(() => {
    for (const key of keys) {
      if (originalEnv[key] === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = originalEnv[key];
      }
    }
  });

  function clearPublicEnv() {
    for (const key of keys) {
      originalEnv[key] = process.env[key];
      delete process.env[key];
    }
  }

  it('returns empty string for undefined', () => {
    clearPublicEnv();
    expect(getMediaUrl(undefined)).toBe('');
  });

  it('returns path as-is when it starts with http', () => {
    clearPublicEnv();
    expect(getMediaUrl('https://cdn.example.com/img.png')).toBe('https://cdn.example.com/img.png');
    expect(getMediaUrl('http://localhost/media/x.png')).toBe('http://localhost/media/x.png');
  });

  it('prepends base URL for path starting with /', () => {
    clearPublicEnv();
    process.env.NEXT_PUBLIC_API_URL = 'http://api.test';
    expect(getMediaUrl('/media/photo.jpg')).toBe('http://api.test/media/photo.jpg');
  });

  it('prepends base URL and / for path without leading slash', () => {
    clearPublicEnv();
    process.env.NEXT_PUBLIC_API_URL = 'http://api.test';
    expect(getMediaUrl('media/photo.jpg')).toBe('http://api.test/media/photo.jpg');
  });

  it('uses localhost:8000 when NEXT_PUBLIC_API_URL is not set', () => {
    clearPublicEnv();
    expect(getMediaUrl('/media/x.png')).toBe('http://localhost:8000/media/x.png');
  });

  it('keeps relative /media when site origin prefers same-origin media', () => {
    clearPublicEnv();
    process.env.NEXT_PUBLIC_SITE_URL = 'http://localhost:3000';
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000';
    expect(getMediaUrl('/media/x.png')).toBe('/media/x.png');
  });
});
