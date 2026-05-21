/**
 * Нагрузочный тест API Ringoo (k6).
 *
 * Запуск:
 *   k6 run --vus 1000 --duration 5m scripts/load-test-k6.js
 *   BASE_URL=https://api.ringoo.ru k6 run --vus 500 --duration 3m scripts/load-test-k6.js
 *
 * Цели: симулировать 1000 одновременных пользователей; проверить каталог, заказы, очереди.
 */

import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";
const API = `${BASE_URL}/api/v1`;

export const options = {
  stages: [
    { duration: "1m", target: 200 },
    { duration: "2m", target: 1000 },
    { duration: "2m", target: 1000 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<3000"],
  },
};

export default function () {
  const res = http.get(`${API}/products/categories/`);
  check(res, { "categories status 200": (r) => r.status === 200 });
  sleep(0.5);

  const list = http.get(
    `${API}/products/products/?page=1&page_size=20&ordering=created_at`
  );
  check(list, { "products list status 200": (r) => r.status === 200 });
  sleep(0.3);

  const brands = http.get(`${API}/products/products/brands/`);
  check(brands, { "brands status 200": (r) => r.status === 200 });
  sleep(0.2);
}
