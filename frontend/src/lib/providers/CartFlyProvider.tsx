'use client';

import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { motion } from 'framer-motion';
import { ShoppingBag } from 'lucide-react';

interface CartFlyContextValue {
  registerCartRef: (el: HTMLButtonElement | null) => void;
  triggerFly: (fromRect: DOMRect) => void;
}

const CartFlyContext = createContext<CartFlyContextValue | null>(null);

export function useCartFly() {
  const ctx = useContext(CartFlyContext);
  return ctx;
}

export function CartFlyProvider({ children }: { children: ReactNode }) {
  const cartRef = useRef<HTMLButtonElement | null>(null);
  const [flyState, setFlyState] = useState<{
    from: DOMRect;
    to: DOMRect;
  } | null>(null);

  const registerCartRef = useCallback((el: HTMLButtonElement | null) => {
    cartRef.current = el;
  }, []);

  const triggerFly = useCallback((fromRect: DOMRect) => {
    const cartEl = cartRef.current;
    if (!cartEl) return;
    const toRect = cartEl.getBoundingClientRect();
    setFlyState({ from: fromRect, to: toRect });
    const t = setTimeout(() => setFlyState(null), 420);
    return () => clearTimeout(t);
  }, []);

  return (
    <CartFlyContext.Provider value={{ registerCartRef, triggerFly }}>
      {children}
      {typeof document !== 'undefined' &&
        flyState &&
        createPortal(
          <motion.div
            className="fixed left-0 top-0 z-[9999] pointer-events-none flex items-center justify-center"
            style={{
              width: 24,
              height: 24,
            }}
            initial={{
              x: flyState.from.left + flyState.from.width / 2 - 12,
              y: flyState.from.top + flyState.from.height / 2 - 12,
              opacity: 1,
              scale: 1,
            }}
            animate={{
              x: flyState.to.left + flyState.to.width / 2 - 12,
              y: flyState.to.top + flyState.to.height / 2 - 12,
              opacity: 0,
              scale: 0.5,
            }}
            transition={{
              duration: 0.4,
              ease: [0.25, 0.46, 0.45, 0.94],
            }}
          >
            <div className="rounded-full bg-brand p-1 text-white">
              <ShoppingBag className="h-4 w-4" />
            </div>
          </motion.div>,
          document.body
        )}
    </CartFlyContext.Provider>
  );
}
