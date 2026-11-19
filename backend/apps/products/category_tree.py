"""
Обход иерархии Category (1С adjacency list) без MPTT.

Защита от циклов parent. Не меняет данные.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable
from uuid import UUID

from django.db.models import QuerySet

from .models import Category


def iter_descendant_ids(
    root_id: UUID | str,
    *,
    categories: Iterable[Category] | None = None,
) -> list[UUID]:
    """
    Все потомки root (без самого root), BFS.
    categories — опционально предзагруженный список для избежания N+1.
    """
    root = str(root_id)
    if categories is None:
        pairs = list(Category.objects.values_list("id", "parent_id"))
    else:
        pairs = [(c.id, c.parent_id) for c in categories]

    children_map: dict[str, list[UUID]] = defaultdict(list)
    for cid, parent_id in pairs:
        if parent_id:
            children_map[str(parent_id)].append(cid)

    result: list[UUID] = []
    seen: set[str] = {root}
    queue: deque[str] = deque([root])
    while queue:
        current = queue.popleft()
        for child_id in children_map.get(current, []):
            key = str(child_id)
            if key in seen:
                continue
            seen.add(key)
            result.append(child_id)
            queue.append(key)
    return result


def category_and_descendant_ids(root: Category) -> list[UUID]:
    """id корня + все потомки."""
    return [root.id, *iter_descendant_ids(root.id)]


def filter_products_in_category_subtree(qs: QuerySet, category: Category) -> QuerySet:
    """Товары в категории и во всех вложенных папках 1С."""
    ids = category_and_descendant_ids(category)
    return qs.filter(category_id__in=ids)
