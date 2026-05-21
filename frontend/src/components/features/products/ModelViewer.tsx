'use client';

import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';

/** Placeholder 3D-сцена (замена галерее для товаров с has_3d_model) */
function ModelPlaceholder() {
  return (
    <mesh>
      <boxGeometry args={[1, 0.1, 2]} />
      <meshStandardMaterial color="#22c55e" roughness={0.3} metalness={0.7} />
    </mesh>
  );
}

interface ModelViewerProps {
  /** URL GLB-модели (пока не используется) */
  modelUrl?: string;
  className?: string;
}

/**
 * 3D-просмотрщик модели товара.
 * DESIGN_SPEC: OrbitControls, fallback — галерея.
 * Пока рендерит placeholder; при наличии modelUrl можно загрузить GLB.
 */
export function ModelViewer({ modelUrl, className }: ModelViewerProps) {
  return (
    <div className={className}>
      <Suspense
        fallback={<div className="aspect-square w-full animate-pulse rounded-xl bg-zinc-200" />}
      >
        <Canvas camera={{ position: [0, 0, 4], fov: 45 }} dpr={[1, 2]} gl={{ antialias: true }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[3, 3, 3]} intensity={1} />
          <ModelPlaceholder />
          <OrbitControls
            enableZoom
            enablePan={false}
            minPolarAngle={Math.PI / 4}
            maxPolarAngle={Math.PI / 2}
          />
        </Canvas>
      </Suspense>
    </div>
  );
}
