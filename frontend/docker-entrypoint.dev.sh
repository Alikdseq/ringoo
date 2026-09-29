#!/bin/sh

# Опциональные манифесты статики (magazins / menegers)
if [ -f scripts/generate-magazins-manifest.mjs ]; then
  node scripts/generate-magazins-manifest.mjs 2>/dev/null || true
fi
if [ -f scripts/generate-menegers-manifest.mjs ]; then
  node scripts/generate-menegers-manifest.mjs 2>/dev/null || true
fi

exec "$@"
