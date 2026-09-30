import { describe, it, expect, afterEach } from 'vitest';
import { getMediaUrl } from './image-url';

describe('getMediaUrl', () => {
  const originalEnv = process.env.NEXT_PUBLIC_API_URL;

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_URL = originalEnv;
  });

  it('returns empty string for undefined', () => {
    expect(getMediaUrl(undefined)).toBe('');
  });

  it('returns path as-is when it starts with http', () => {
    expect(getMediaUrl('https://cdn.example.com/img.png')).toBe('https://cdn.example.com/img.png');
    expect(getMediaUrl('http://localhost/media/x.png')).toBe('http://localhost/media/x.png');
  });

  it('prepends base URL for path starting with /', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://api.test';
    expect(getMediaUrl('/media/photo.jpg')).toBe('http://api.test/media/photo.jpg');
  });

  it('prepends base URL and / for path without leading slash', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://api.test';
    expect(getMediaUrl('media/photo.jpg')).toBe('http://api.test/media/photo.jpg');
  });

  it('uses localhost:8000 when NEXT_PUBLIC_API_URL is not set', () => {
    delete process.env.NEXT_PUBLIC_API_URL;
    expect(getMediaUrl('/media/x.png')).toBe('http://localhost:8000/media/x.png');
  });
});
