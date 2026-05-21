'use client';

import { useRef, useState, useCallback, type ReactNode } from 'react';
import { motion } from 'framer-motion';
import { useCanUse3DTilt } from '@/lib/utils/canUse3D';
import { cn } from '@/lib/theme/utils';

const MAX_TILT = 5; // градусы

interface Card3DTiltProps {
  children: ReactNode;
  className?: string;
  /** Отключить tilt принудительно */
  disableTilt?: boolean;
}

export function Card3DTilt({ children, className, disableTilt }: Card3DTiltProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [rotate, setRotate] = useState({ x: 0, y: 0 });
  const canTilt = useCanUse3DTilt();
  const tiltEnabled = !disableTilt && canTilt;

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!tiltEnabled || !cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const x = (e.clientX - centerX) / (rect.width / 2);
      const y = (e.clientY - centerY) / (rect.height / 2);
      setRotate({
        x: Math.max(-1, Math.min(1, -y)) * MAX_TILT,
        y: Math.max(-1, Math.min(1, x)) * MAX_TILT,
      });
    },
    [tiltEnabled]
  );

  const handleMouseLeave = useCallback(() => {
    setRotate({ x: 0, y: 0 });
  }, []);

  return (
    <motion.div
      ref={cardRef}
      className={cn(tiltEnabled && 'perspective-[1000px] [transform-style:preserve-3d]', className)}
      onMouseMove={tiltEnabled ? handleMouseMove : undefined}
      onMouseLeave={tiltEnabled ? handleMouseLeave : undefined}
      animate={{
        rotateX: tiltEnabled ? rotate.x : 0,
        rotateY: tiltEnabled ? rotate.y : 0,
      }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      {children}
    </motion.div>
  );
}
