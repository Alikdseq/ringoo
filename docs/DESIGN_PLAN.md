# АТОМАРНЫЙ ПЛАН РАЗРАБОТКИ ДИЗАЙНА RINGOO

## Основа: docs/DESIGN_SPEC.md

---

## 📋 ОГЛАВЛЕНИЕ

1. [ЭТАП D1: Дизайн-система (цвета, типографика, токены)](#этап-d1)
2. [ЭТАП D2: UI-компоненты](#этап-d2)
3. [ЭТАП D3: Layout и страницы](#этап-d3)
4. [ЭТАП D4: Микроанимации и переходы](#этап-d4)
5. [ЭТАП D5: 3D-эффекты и Hero](#этап-d5)
6. [ЭТАП D6: Полировка и производительность](#этап-d6)

---

## ЭТАП D1: ДИЗАЙН-СИСТЕМА (цвета, типографика, токены)

### D1.1 Цветовая палитра

**Задача D1.1.1:** Обновить globals.css
- [x] Установить светлую тему по умолчанию в `:root`
- [x] Удалить приоритет тёмной темы; `--background: #f9fafb`, `--foreground: #020617`
- [x] Добавить все переменные из DESIGN_SPEC §2
- [x] Убрать или инвертировать логику `prefers-color-scheme: light`

**Задача D1.1.2:** Обновить colors.ts
- [x] Синхронизировать с палитрой DESIGN_SPEC §2
- [x] Добавить `backgroundAlt`, `foregroundMuted`, `foregroundSubtle`, `border`, `borderDark`
- [x] Экспортировать константы для использования в компонентах

**Задача D1.1.3:** Расширить Tailwind
- [x] Добавить в `@theme inline` (globals.css) кастомные цвета (brand, brand-soft, brand-muted)
- [x] Добавить семантические цвета (success, danger, warning, info)
- [x] Классы доступны через Tailwind v4 @theme (bg-brand, text-brand, border-border и т.д.)

### D1.2 Типографика

**Задача D1.2.1:** Создать/обновить typography.ts
- [x] Определить размеры H1–H3, Body, Body Small, Caption, Button
- [x] Определить font-weight и line-height
- [x] Экспортировать утилиты или классы для применения

**Задача D1.2.2:** Расширить Tailwind типографикой
- [x] Добавить в @theme (globals.css) кастомные fontSize: text-h1, text-h2, text-h3, text-body, text-body-small, text-caption, text-button
- [x] Добавить tracking-tight (-0.02em) для заголовков
- [x] Geist подключён в layout.tsx (next/font)

### D1.3 Spacing и Layout

**Задача D1.3.1:** Зафиксировать spacing-токены
- [x] Проверить соответствие: 1=4px, 2=8px, 4=16px, 6=24px, 8=32px, 12=48px (xs…2xl)
- [x] Создать spacing.ts: SPACING, CONTAINER_MAX_WIDTH, CONTAINER_CLASS; задокументировать max-width 1280px и отступы по breakpoints

---

## ЭТАП D2: UI-КОМПОНЕНТЫ

### D2.1 Button

**Задача D2.1.1:** Привести Button к спецификации
- [x] Primary: brand, white text, pill (rounded-full)
- [x] Hover: darken brand (emerald-600)
- [x] Active: scale(0.98)
- [x] Loading: spinner (border-current opacity-70)
- [x] Variants: primary, secondary, outline, ghost — светлая тема, добавлен asChild

### D2.2 Card

**Задача D2.2.1:** Обновить Card
- [x] Фон: white, тень: shadow-sm, скругление: rounded-xl
- [x] interactive: hover shadow-md + translateY(-2px), 150ms
- [x] Граница: border-border, убраны dark: варианты

### D2.3 Input

**Задача D2.3.1:** Обновить Input
- [x] Светлая тема: border-border, placeholder:text-foreground-subtle
- [x] Focus: ring-brand
- [x] Error: border-danger
- [x] Disabled: opacity 0.6

### D2.4 Modal

**Задача D2.4.1:** Обновить Modal
- [x] Overlay: bg-black/50, backdrop-blur
- [x] Появление/закрытие: opacity + scale, 200–220ms

### D2.5 Чипсы и бейджи

**Задача D2.5.1:** Создать Chip-компонент
- [x] Chip, ChipList: filter (brand-soft), removable с крестиком
- [x] Hover: brand, анимация 150ms

**Задача D2.5.2:** Обновить бейджи скидок
- [x] Badge, DiscountBadge: danger, формат −X%, top-right (использован в ProductCard)

### D2.6 Loading и Skeleton

**Задача D2.6.1:** Обновить Loading
- [x] Spinner: border-brand/30 border-t-brand
- [x] Skeleton: bg-zinc-200, animate-skeleton-shimmer

---

## ЭТАП D3: LAYOUT И СТРАНИЦЫ

### D3.1 Header

**Задача D3.1.1:** Привести Header к светлой теме
- [x] Фон: white/80, backdrop-blur, sticky
- [x] Граница: border-border
- [x] Навигация: text-foreground, hover:text-brand
- [x] Логотип: text-brand
- [x] Корзина: иконка + badge brand
- [x] Убраны dark: классы

### D3.2 Footer

**Задача D3.2.1:** Обновить Footer
- [x] Фон: zinc-50, текст: text-foreground-muted
- [x] Ссылки: hover:text-brand
- [x] Светлая тема

### D3.3 MobileMenu

**Задача D3.3.1:** Обновить MobileMenu
- [x] Off-canvas, slide-анимация 220ms
- [x] Фон: white, border-border

### D3.4 Главная страница

**Задача D3.4.1:** Обновить HeroSection
- [x] Фон: градиент brand-soft
- [x] Светлая тема, TYPOGRAPHY
- [x] Кнопка CTA: brand, pill, параллакс

**Задача D3.4.2:** Обновить секции главной
- [x] HomeFeatures: H2, H3, карточки с hover
- [x] HomeCta: светлая тема
- [x] Spacing, border-border

### D3.5 Каталог

**Задача D3.5.1:** Обновить страницу каталога
- [x] Фильтры: sidebar (desktop), drawer (mobile)
- [x] Чипсы над grid (brand-soft)
- [x] Grid: 2/3/4 колонки
- [x] Светлая тема

### D3.6 ProductCard

**Задача D3.6.1:** Обновить ProductCard
- [x] Card interactive, DiscountBadge
- [x] Текст: foreground, foreground-muted
- [x] Бейдж скидки: danger (в D2)

### D3.7 PDP (страница товара)

**Задача D3.7.1:** Обновить PDP
- [x] Галерея, блок цены, CTA
- [x] border-border, rounded-xl
- [x] Светлая тема (частично)

### D3.8 Корзина

**Задача D3.8.1:** Обновить страницу корзины
- [x] Список CartItem, поле промокода, итог, CTA brand
- [x] Пустая корзина: text-foreground-muted, CTA
- [x] Светлая тема (text-foreground, text-danger)

### D3.9 Checkout

**Задача D3.9.1:** Обновить checkout
- [ ] Stepper, формы — оставлены dark: (требует доработки)
- [x] Input, Card, Button — компоненты обновлены в D2

### D3.10 Личный кабинет

**Задача D3.10.1:** Обновить profile
- [ ] Остались dark: классы (требует доработки)
- [x] Card, Button — компоненты обновлены

### D3.11 Блог и Новости

**Задача D3.11.1:** Обновить blog page
- [ ] BlogContent — остались dark: (требует доработки)

**Задача D3.11.2:** blog/[slug] — по PLAN.md не создан
**Задача D3.11.3:** news page — по PLAN.md не создан

### D3.12 Акции

**Задача D3.12.1:** Обновить promotions
- [x] Карточки акций, таймер (warning/danger)
- [x] Светлая тема (text-foreground, text-foreground-muted)

### D3.13 Магазины

**Задача D3.13.1:** Страница магазинов
- [ ] app/stores не создана (в PLAN — отдельная страница)
- StoreSelector, StoresMap — остались dark: (требует доработки)

---

## ЭТАП D4: МИКРОАНИМАЦИИ И ПЕРЕХОДЫ

### D4.1 Переходы между страницами

**Задача D4.1.1:** Настроить page transitions
- [x] Framer Motion в AppShell (AnimatePresence + motion.div)
- [x] Анимация: fade + slide (y: 8→0, exit y: -4), 250ms
- [x] Навигация работает

### D4.2 Hero-параллакс

**Задача D4.2.1:** Hero-параллакс
- [x] useScroll + useTransform: yBg, opacityBg, yContent, opacityContent
- [x] transform/opacity — 60 FPS

### D4.3 Карточки товаров — hover

**Задача D4.3.1:** Карточки: подъём + тень
- [x] Card interactive: hover:-translate-y-0.5, shadow-md
- [x] transition 150ms ease-out

### D4.4 Элементы при скролле

**Задача D4.4.1:** Scroll reveal
- [x] ScrollRevealSection: useInView + Framer Motion
- [x] Появление снизу (y: 32→0), duration 300ms
- [x] Stagger в HomeFeatures через transition.delay

### D4.5 Добавление в корзину — «летящая иконка»

**Задача D4.5.1:** Fly-to-cart
- [x] CartFlyProvider, useCartFly
- [x] Анимация иконки от кнопки к корзине (x, y, opacity, scale), ~400ms
- [x] ProductCard: triggerFly при клике; fallback: scale-пульс на кнопке

### D4.6 Чипсы фильтров

**Задача D4.6.1:** Анимация чипов
- [x] Chip + ChipList с AnimatePresence mode="popLayout"
- [x] initial/animate/exit 150ms, интеграция в каталог

### D4.7 Модальные окна

**Задача D4.7.1:** Анимация модалок
- [x] opacity 0→1, scale 0.95→1, 220ms (уже в D2)

---

## ЭТАП D5: 3D-ЭФФЕКТЫ И HERO

### D5.1 Инфраструктура 3D

**Задача D5.1.1:** Установить зависимости
- [x] three, @react-three/fiber, @react-three/drei, @types/three

**Задача D5.1.2:** Утилита определения возможностей 3D
- [x] canUse3D(): prefers-reduced-motion, hardwareConcurrency > 4
- [x] canUse3DTilt(): без touch
- [x] useCanUse3D, useCanUse3DTilt (hydration-safe)

### D5.2 Hero 3D

**Задача D5.2.1:** Hero3D компонент
- [x] Canvas, RoundedBox (placeholder телефона)
- [x] Ambient + Directional light
- [x] Вращение по Y ~7°/с (useFrame)
- [x] Float от drei
- [x] dynamic import, ssr: false

**Задача D5.2.2:** Интеграция в HeroSection
- [x] useCanUse3D(): 3D или fallback градиент
- [x] Parallax (yBg, opacityBg) общий для обоих

**Задача D5.2.3:** GLB-модель
- [ ] Placeholder; GLB/Draco — при наличии ассетов

### D5.3 Карточка каталога — 3D tilt

**Задача D5.3.1:** 3D tilt на ProductCard
- [x] Card3DTilt: perspective, preserve-3d
- [x] rotateX/rotateY по курсору, max ±5°
- [x] useCanUse3DTilt: fallback на touch
- [x] Обёртка ProductCard

### D5.4 PDP — ModelViewer (опционально)

**Задача D5.4.1:** ModelViewer компонент
- [x] Canvas, OrbitControls
- [x] Placeholder mesh (box)
- [ ] GLB-загрузка — при наличии моделей

**Задача D5.4.2:** Интеграция в PDP
- [ ] Переключатель 3D/Галерея — по необходимости

---

## ЭТАП D6: ПОЛИРОВКА И ПРОИЗВОДИТЕЛЬНОСТЬ

### D6.1 Удаление тёмной темы

**Задача D6.1.1:** Очистить проект от dark: классов
- [ ] Найти все dark: в компонентах
- [ ] Заменить на светлые эквиваленты или удалить
- [ ] Проверить Header, Footer, Card, Input, ProductCard и др.

### D6.2 Консистентность

**Задача D6.2.1:** Пройтись по всем страницам
- [ ] Единый фон (background)
- [ ] Единые отступы
- [ ] Единая типографика заголовков

### D6.3 Производительность

**Задача D6.3.1:** Проверить анимации
- [ ] Использовать только transform и opacity
- [ ] Добавить will-change где необходимо (осторожно)
- [ ] Убрать layout-triggering свойства из анимаций

**Задача D6.3.2:** Lighthouse аудит
- [ ] Запуск Lighthouse на Production build
- [ ] Цель: Performance > 85
- [ ] Исправить выявленные проблемы (изображения, шрифты, JS)

### D6.4 Адаптивность

**Задача D6.4.1:** Проверить breakpoints
- [ ] Mobile: 1–2 колонки, бургер, упрощённый Hero
- [ ] Tablet: 2–3 колонки
- [ ] Desktop: 4 колонки, полный функционал

**Задача D6.4.2:** Touch-устройства
- [ ] Убедиться, что 3D tilt не мешает на тач-устройствах
- [ ] Увеличить hit-area кнопок на mobile

### D6.5 prefers-reduced-motion

**Задача D6.5.1:** Уважать prefers-reduced-motion
- [ ] Отключить 3D при prefers-reduced-motion: reduce
- [ ] Упростить или убрать параллакс
- [ ] Оставить только необходимые transition (opacity)

---

## 📊 СВОДКА ЗАДАЧ

| Этап | Задач | Оценка |
|------|-------|--------|
| D1 | 7 | 1–2 дня |
| D2 | 11 | 2–3 дня |
| D3 | 18 | 3–4 дня |
| D4 | 7 | 1–2 дня |
| D5 | 8 | 2–3 дня |
| D6 | 6 | 1–2 дня |
| **Итого** | **~57** | **10–16 дней** |

---

## 📝 ПРИМЕЧАНИЯ

1. Этапы D1–D3 можно выполнять последовательно; D4 можно частично параллелить с D3.
2. D5 (3D) — опционален для MVP; можно отложить и оставить fallback.
3. После D6 — финальная проверка по DESIGN_SPEC и ТЗ.txt.
