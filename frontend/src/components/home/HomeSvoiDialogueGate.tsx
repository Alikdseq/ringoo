'use client';

import { useUiMode } from '@/lib/providers/UiModeProvider';
import { HeroSvoiZinaBolaBanner } from '@/components/home/HeroSvoiZinaBolaBanner';

/** Баннер Зина/Бола только в свойском режиме; режим синхронизирован с сервером через cookie → без рассинхрона гидратации. */
export function HomeSvoiDialogueGate() {
  const { mode } = useUiMode();
  if (mode !== 'svoi') return null;
  return <HeroSvoiZinaBolaBanner />;
}
