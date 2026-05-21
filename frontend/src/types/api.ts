// Базовые типы ответов API (будут расширяться по мере реализации фронтенда)

// --- Общие обёртки ---

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type ApiResponse<T> = T;
export type PaginatedResponse<T> = Paginated<T>;

// --- Справочники / каталог ---

export interface Category {
  id: string;
  title: string;
  slug: string;
  parent: string | null;
  description: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
}

export interface ProductColor {
  id: string;
  slug: string;
  label: string;
  hex: string | null;
  sort_order: number;
  is_active: boolean;
  /** Своя цена варианта; null — цена товара */
  price?: string | null;
  old_price?: string | null;
}

export interface ProductImage {
  id: string;
  image: string;
  is_main: boolean;
  alt_text: string | null;
  /** Нет у снимков «недавно смотрели» и у части ответов списка */
  color?: ProductColor | null;
  sort_order?: number;
}

export interface ProductListColor extends ProductColor {
  /** В списке товаров; на PDP может отсутствовать */
  preview_image?: string | null;
  preview_alt?: string | null;
}

export interface Product {
  id: string;
  title: string;
  slug: string;
  price: string;
  old_price: string | null;
  rating: number;
  reviews_count: number;
  category: Category;
  short_description?: string | null;
  images?: ProductImage[];
  /** В списке товаров: цвета с превью для переключателя на карточке */
  colors?: ProductListColor[];
  discount_percent?: number;
  is_featured?: boolean;
  /** Дата создания (список товаров) — для бейджа «Новинка» */
  created_at?: string;
  /** Суммарное доступное количество по всем складам (для отображения «В наличии: N шт») */
  available_quantity_total?: number;
  /** Статус наличия: влияет на кнопку «В корзину» */
  availability_status?: 'in_stock' | 'out_of_stock';
}

export interface ProductSpec {
  name: string;
  value: string;
}

export interface ProductDetail extends Omit<Product, 'colors'> {
  sku: string;
  description: string;
  brand: string;
  is_active: boolean;
  specs: ProductSpec[];
  /** Варианты цвета (PDP); пусто — одна общая галерея */
  colors?: ProductColor[];
  stock: Stock[];
  is_in_user_cart: boolean;
  created_at: string;
  updated_at: string;
  meta_title?: string | null;
  meta_description?: string | null;
  /** Есть ли 3D-модель (API, опционально) */
  has_3d_model?: boolean;
  /** URL GLB-модели (API, опционально) */
  model_3d_url?: string | null;
}

export interface Store {
  id: string;
  name: string;
  slug: string;
  city: string;
  address: string;
  phone: string | null;
  coordinates: {
    latitude: string;
    longitude: string;
  } | null;
  working_hours: Record<string, string> | null;
}

export interface Stock {
  product: string; // UUID
  store: string; // UUID
  quantity: number;
  available_quantity: number;
}

// --- Пользователь и аутентификация ---

export interface UserProfile {
  first_name: string | null;
  last_name: string | null;
  middle_name: string | null;
  avatar: string | null;
  birth_date: string | null;
  gender: string | null;
}

export interface User {
  id: string;
  phone: string;
  email: string | null;
  is_phone_verified: boolean;
  is_email_verified: boolean;
  created_at: string;
  updated_at: string;
  /** ISO datetime — фиксация согласия с политикой при регистрации */
  privacy_policy_accepted_at?: string | null;
  marketing_opt_in?: boolean;
  marketing_opt_in_at?: string | null;
  profile?: UserProfile | null;
}

export interface DeliveryAddress {
  id: number;
  title: string;
  city: string;
  street: string;
  house: string;
  apartment: string | null;
  postal_code: string | null;
  is_default: boolean;
  latitude: string | null;
  longitude: string | null;
  created_at: string;
  updated_at: string;
}

// --- Корзина ---

export interface WishlistItem {
  id: string;
  product: Product;
  created_at: string;
}

export interface CartItem {
  id: string;
  product: Product;
  store: Store | null;
  color?: ProductColor | null;
  quantity: number;
  price_at_add: string;
  item_total: string;
  created_at: string;
  updated_at: string;
}

export interface Cart {
  id: string;
  items: CartItem[];
  total_amount: string;
  created_at: string;
  updated_at: string;
}

// --- Заказы ---

export interface OrderItem {
  id: string;
  product_title: string;
  quantity: number;
  price: string;
  item_total: string;
}

export interface Order {
  id: string;
  order_number: string;
  full_name: string;
  phone: string;
  email: string | null;
  delivery_type: string;
  delivery_address: Record<string, unknown>;
  store: string | null;
  payment_type: string;
  status: string;
  total_amount: string;
  delivery_cost: string;
  bonus_used: string;
  bonus_earned: string;
  comment: string | null;
  items: OrderItem[];
  created_at: string;
  updated_at: string;
  /** Есть ли оценка менеджера по этому заказу (для ЛК). */
  has_rating?: boolean;
}

// --- Блог / контент ---

export interface ContentTag {
  id: string;
  name: string;
  slug: string;
}

export interface ArticleList {
  id: string;
  title: string;
  slug: string;
  excerpt: string | null;
  image: string | null;
  category: string | null;
  tags: ContentTag[];
  published_at: string | null;
  views_count: number;
  created_at: string;
}

/** Публичный список новостей (`GET /content/news/`). */
export interface NewsList {
  id: string;
  title: string;
  slug: string;
  excerpt: string | null;
  image: string | null;
  category: string | null;
  tags: ContentTag[];
  is_featured: boolean;
  published_at: string | null;
  views_count: number;
  created_at: string;
}

export interface Promotion {
  id: string;
  title: string;
  description: string | null;
  image: string | null;
  discount_type: 'percent' | 'fixed';
  discount_value: string;
  start_date: string;
  end_date: string;
  category_slugs: string[];
  created_at: string;
}
