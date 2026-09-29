'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="ru">
      <body
        style={{
          margin: 0,
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        <main style={{ maxWidth: 420, padding: 24, textAlign: 'center' }}>
          <h1 style={{ fontSize: 22, marginBottom: 8 }}>Ошибка</h1>
          <p style={{ color: '#52525b', marginTop: 0 }}>
            Страница не загрузилась. Обновите её или вернитесь позже.
          </p>
          <p style={{ display: 'none' }}>{error.digest ?? ''}</p>
          <button
            type="button"
            onClick={() => reset()}
            style={{
              border: 0,
              borderRadius: 999,
              padding: '10px 18px',
              background: '#16a34a',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            Попробовать снова
          </button>
        </main>
      </body>
    </html>
  );
}
