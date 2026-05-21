'use client';

import { useRef } from 'react';
import { motion, useInView, useReducedMotion, type Transition, type Variants } from 'framer-motion';

const defaultVariants: Variants = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0 },
};

const defaultTransition: Transition = {
  duration: 0.3,
  ease: [0.25, 0.46, 0.45, 0.94],
};

interface ScrollRevealSectionProps {
  children: React.ReactNode;
  className?: string;
  /** Использовать только transform и opacity для 60 FPS */
  variants?: Variants;
  transition?: Transition;
  amount?: number;
}

export function ScrollRevealSection({
  children,
  className = '',
  variants = defaultVariants,
  transition = defaultTransition,
  amount = 0.2,
}: ScrollRevealSectionProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, amount });
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      ref={ref}
      className={className}
      initial="hidden"
      animate={prefersReducedMotion ? 'visible' : isInView ? 'visible' : 'hidden'}
      variants={variants}
      transition={transition}
    >
      {children}
    </motion.div>
  );
}
