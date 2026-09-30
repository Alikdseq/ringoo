'use client';

import {
  createContext,
  useCallback,
  useContext,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { UiMode } from '@/lib/ui-mode/types';
import { UI_MODE_SVOI_ENABLED } from '@/lib/ui-mode/featureFlags';
import {
  applyUiModeToDocument,
  persistUiMode,
  readPersistedUiMode,
} from '@/lib/ui-mode/storage';

type Ctx = {
  mode: UiMode;
  setMode: (m: UiMode) => void;
  toggleMode: () => void;
};

const UiModeContext = createContext<Ctx | null>(null);

/** Тот же приоритет, что в bootstrap в layout: cookie → localStorage → сервер. */
function resolveUiMode(initialMode: UiMode): UiMode {
  if (!UI_MODE_SVOI_ENABLED) return 'official';
  if (typeof window === 'undefined') return initialMode;
  return readPersistedUiMode() ?? initialMode;
}

export function UiModeProvider({
  children,
  initialMode,
}: {
  children: ReactNode;
  /** Совпадает с cookie `ringoo_ui_mode` на сервере — первая отрисовка = SSR, без рассинхрона гидратации. */
  initialMode: UiMode;
}) {
  const [mode, setModeState] = useState<UiMode>(() => resolveUiMode(initialMode));

  useLayoutEffect(() => {
    applyUiModeToDocument(UI_MODE_SVOI_ENABLED ? mode : 'official');
  }, [mode]);

  const setMode = useCallback((m: UiMode) => {
    if (!UI_MODE_SVOI_ENABLED) return;
    setModeState(m);
    persistUiMode(m);
    applyUiModeToDocument(m);
  }, []);

  const toggleMode = useCallback(() => {
    if (!UI_MODE_SVOI_ENABLED) return;
    setModeState(prev => {
      const next: UiMode = prev === 'official' ? 'svoi' : 'official';
      persistUiMode(next);
      applyUiModeToDocument(next);
      return next;
    });
  }, []);

  const value = useMemo(() => ({ mode, setMode, toggleMode }), [mode, setMode, toggleMode]);

  return <UiModeContext.Provider value={value}>{children}</UiModeContext.Provider>;
}

export function useUiMode(): Ctx {
  const ctx = useContext(UiModeContext);
  if (!ctx) {
    throw new Error('useUiMode must be used within UiModeProvider');
  }
  return ctx;
}
