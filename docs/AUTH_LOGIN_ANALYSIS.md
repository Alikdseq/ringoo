# Анализ: 400 / «неправильный логин или пароль» при входе

## Цепочка: регистрация → сохранение → вход

### Регистрация (RegisterSerializer)

1. **validate_phone(value)** возвращает **нормализованный** номер: `normalize_phone(value)` → например `"79187020987"`.
2. **create()** вызывает `CustomUser.objects.create_user(**validated_data, password=password)`.
3. После `pop` в `validated_data` остаётся только `phone` (нормализованный).
4. В БД пользователь сохраняется с `phone="79187020987"`, пароль хэшируется через `set_password(password)`.

### Вход (POST /api/v1/auth/token/)

1. Фронт отправляет JSON: `{ "username": "79187020987", "password": "..." }`.
2. В представлении мы подменяем `request._full_data` этим объектом и вызываем `super().post()`.
3. Родительский класс создаёт сериализатор: `CustomTokenObtainPairSerializer(data=request.data)` и вызывает `is_valid(raise_exception=True)`.

## Корень проблемы

**SimpleJWT** в `TokenObtainSerializer` (родитель `TokenObtainPairSerializer`) задаёт имя поля логина так:

```python
# rest_framework_simplejwt/serializers.py, строка 31
username_field = get_user_model().USERNAME_FIELD
# ...
self.fields[self.username_field] = serializers.CharField(write_only=True)  # строка 40
```

У нас `CustomUser.USERNAME_FIELD = "phone"`. Поэтому сериализатор объявляет поля **"phone"** и **"password"**, а не "username" и "password".

В результате:

- Тело запроса: `{ "username": "79187020987", "password": "..." }`.
- Сериализатор ожидает обязательное поле **"phone"**. Ключа `"phone"` в данных нет → при `is_valid()` срабатывает полевая валидация → **ValidationError** → ответ **400 Bad Request**.
- Наш метод `CustomTokenObtainPairSerializer.validate()` **никогда не вызывается**: ошибка возникает раньше, в `to_internal_value()` родителя. До `authenticate()` выполнение не доходит, поэтому сообщение «неправильный логин или пароль» или 400 появляются даже при верных данных.

Итог: несовпадение имени поля в API (мы шлём `username`) и имени поля сериализатора SimpleJWT (`phone` = `USERNAME_FIELD`) — **корневая причина** ошибки.

## План исправления

1. **В представлении** `TokenObtainPairViewNoCSRF.post()` при подготовке тела запроса для сериализатора явно подставлять поле `"phone"`, если фронт прислал только `"username"`:
   - `data["phone"] = data.get("phone") or data.get("username")`.
   - Так родительский сериализатор получит обязательное поле `"phone"`, валидация пройдёт, выполнится наш `validate()` и `authenticate()`.

2. **Фронт** можно оставить с отправкой `username` (для совместимости с типичным «логин/пароль» API) или позже перейти на отправку `phone`; бэкенд будет принимать оба варианта за счёт пункта 1.

3. После исправления при неверном пароле пользователь будет получать **401** с сообщением «No active account found...» (или нашим переводом), а не 400.
