Ниже план реализации именно для твоего текущего каркаса.

Сейчас у тебя уже есть минимальная модель:

* `ContactPointTypeVO` поддерживает `PHONE` и `EMAIL`.
* `ContactPointEntity` хранит `type`, `raw_value`, `normalized_value`, `hash_value`.
* `OwnerContactPointBinding` хранит ссылку на owner через `owner_object_id` и `owner_record_id`.
* `ContactPointBindingEntity` связывает `contact_point_id` с `owner` и хранит `is_primary`.

Это хорошая база. Дальше нужно реализовать два use case:

```text
AttachContactPointUseCase
DetachContactPointUseCase
```

---

# 1. Главная бизнес-модель

```text
ContactPoint
  = глобальная контактная точка внутри tenant

ContactPointBinding
  = связь ContactPoint с конкретной runtime/CRM сущностью
```

Пример:

```text
ContactPoint:
  PHONE +380671112233

Bindings:
  -> Contact #1
  -> Lead #10
  -> CreditApplication #300
```

То есть телефон один, а привязок может быть много.

---

# 2. Главный принцип

`ContactPoint` нельзя создавать дублем, если уже есть такой же normalized/hash.

Правильно:

```text
raw_value: "+38 (067) 111-22-33"
normalized_value: "+380671112233"
hash_value: sha256("+380671112233")
```

Если такой `hash_value` уже есть — новый `ContactPoint` не создаем. Создаем только новую `ContactPointBinding`.

---

# 3. Когда создаем ContactPoint + Binding

Создаем **и ContactPoint, и Binding**, когда:

```text
1. Пользователь добавил phone/email к Contact / Company / Lead / custom object.
2. Значение нормализовалось успешно.
3. В справочнике еще нет ContactPoint с таким type + hash_value.
4. Owner существует.
5. Такой binding еще не существует.
```

Пример:

```text
Contact #100 добавляет phone +380671112233

ContactPoint не найден:
  -> create ContactPoint
  -> create ContactPointBinding(Contact #100 -> ContactPoint)
```

---

# 4. Когда создаем только Binding

Создаем **только Binding**, когда:

```text
1. ContactPoint уже существует.
2. Но он еще не привязан к текущему owner.
```

Пример:

```text
Lead #200 добавляет phone +380671112233

ContactPoint уже есть:
  -> НЕ создаем новый ContactPoint
  -> create ContactPointBinding(Lead #200 -> existing ContactPoint)
```

Это как раз дает контроль дублей.

---

# 5. Когда не создаем ничего

Ничего не создаем, если:

```text
1. ContactPoint уже существует.
2. Binding к этому owner уже существует.
```

UseCase должен быть идемпотентным.

То есть повторный вызов:

```text
Attach PHONE +380671112233 to Contact #100
```

не должен создать второй binding.

Он должен вернуть:

```text
already_attached = true
```

---

# 6. Когда создаем новый ContactPoint при изменении значения

Если пользователь изменяет телефон у Contact:

```text
было: +380671112233
стало: +380501112233
```

Это не “обновление ContactPoint”.

Правильнее:

```text
1. detach old binding
2. attach new ContactPoint
```

Почему: старый `ContactPoint` мог уже участвовать в рассылках, доставках, верификациях, consent, истории коммуникаций.

Нельзя просто перезаписать старый номер.

---

# 7. AttachContactPointUseCase: входные данные

```python
@dataclass(frozen=True, slots=True)
class AttachContactPointCommand:
    owner_object_id: EntityIdVO
    owner_record_id: EntityIdVO

    contact_point_type: ContactPointTypeVO
    raw_value: str

    is_primary: bool = False
```

---

# 8. AttachContactPointUseCase: результат

```python
@dataclass(frozen=True, slots=True)
class AttachContactPointResult:
    contact_point_id: ContactPointIdVO
    binding_id: ContactPointBindingIdVO

    contact_point_created: bool
    binding_created: bool
    already_attached: bool
```

---

# 9. AttachContactPointUseCase: бизнес-логика

```text
1. Проверить, что owner существует.
2. Проверить raw_value.
3. Нормализовать значение.
4. Посчитать hash_value.
5. Найти ContactPoint по type + hash_value.
6. Если ContactPoint не найден — создать ContactPoint.
7. Проверить, есть ли Binding для этого owner + contact_point_id.
8. Если Binding уже есть — вернуть existing binding.
9. Если Binding нет — создать ContactPointBinding.
10. Если is_primary=True:
    - снять primary с других contact points этого owner и этого type;
    - поставить новый binding primary.
11. Сохранить все в одной транзакции.
```

---

# 10. AttachContactPointUseCase: псевдокод

```python
class AttachContactPointUseCase:
    def __init__(
            self,
            uow: ContactPointUnitOfWorkProtocol,
            normalizer: ContactPointNormalizeService,
            hash_service: ContactPointHashService,
            owner_resolver: OwnerResolverPort,
            clock: ClockPort,
            id_generator: IdGeneratorPort,
    ) -> None:
        self._uow = uow
        self._normalizer = normalizer
        self._hash_service = hash_service
        self._owner_resolver = owner_resolver
        self._clock = clock
        self._id_generator = id_generator

    async def execute(
            self,
            command: AttachContactPointCommand,
    ) -> AttachContactPointResult:
        now = self._clock.now()

        owner = OwnerContactPointBinding(
            owner_object_id=command.owner_object_id,
            owner_record_id=command.owner_record_id,
        )

        owner_exists = await self._owner_resolver.exists(owner)

        if not owner_exists:
            raise OwnerNotFoundError(owner)

        normalized_value = self._normalizer.normalize(
            contact_point_type=command.contact_point_type,
            raw_value=command.raw_value,
        )

        hash_value = self._hash_service.hash(normalized_value)

        async with self._uow:
            contact_point = await self._uow.contact_points.get_by_type_and_hash(
                contact_point_type=command.contact_point_type,
                hash_value=hash_value,
            )

            contact_point_created = False

            if contact_point is None:
                contact_point = ContactPointEntity(
                    id=ContactPointIdVO(self._id_generator.new_id()),
                    created_at=now,
                    updated_at=now,
                    type=command.contact_point_type,
                    raw_value=command.raw_value,
                    normalized_value=normalized_value,
                    hash_value=hash_value,
                )

                await self._uow.contact_points.add(contact_point)
                contact_point_created = True

            binding = await self._uow.bindings.get_by_owner_and_contact_point(
                owner=owner,
                contact_point_id=contact_point.id,
            )

            if binding is not None:
                if command.is_primary and not binding.is_primary:
                    await self._uow.bindings.unset_primary_for_owner_and_type(
                        owner=owner,
                        contact_point_type=contact_point.type,
                    )

                    binding.is_primary = True
                    await self._uow.bindings.save(binding)

                await self._uow.commit()

                return AttachContactPointResult(
                    contact_point_id=contact_point.id,
                    binding_id=binding.id,
                    contact_point_created=contact_point_created,
                    binding_created=False,
                    already_attached=True,
                )

            if command.is_primary:
                await self._uow.bindings.unset_primary_for_owner_and_type(
                    owner=owner,
                    contact_point_type=contact_point.type,
                )

            binding = ContactPointBindingEntity(
                id=ContactPointBindingIdVO(self._id_generator.new_id()),
                contact_point_id=contact_point.id,
                owner=owner,
                is_primary=command.is_primary,
            )

            await self._uow.bindings.add(binding)
            await self._uow.commit()

        return AttachContactPointResult(
            contact_point_id=contact_point.id,
            binding_id=binding.id,
            contact_point_created=contact_point_created,
            binding_created=True,
            already_attached=False,
        )
```

---

# 11. Важные инварианты Attach

## Инвариант 1

```text
Один normalized ContactPoint на tenant + type + hash_value.
```

На уровне БД:

```sql
UNIQUE (contact_point_type, hash_value)
```

Таблицы лежат в tenant schema, то `tenant_id` можно не хранить в самой entity.

---

## Инвариант 2

```text
Один binding на owner + contact_point_id.
```

На уровне БД:

```sql
UNIQUE (
    owner_object_id,
    owner_record_id,
    contact_point_id
)
```

---

## Инвариант 3

```text
Один primary ContactPoint одного типа для одного owner.
```

Например:

```text
Contact #100 может иметь:
  PHONE primary: +380671112233
  EMAIL primary: user@example.com
```

Но не два primary `PHONE`.

Делать проверку через join с `ContactPoint`.

---

# 12. DetachContactPointUseCase: смысл

`Detach` удаляет связь между owner и ContactPoint.

Он **не должен по умолчанию удалять ContactPoint**.

```text
Удаляем:
  ContactPointBinding

Оставляем:
  ContactPoint
```

Почему: `ContactPoint` может быть связан с другими объектами или уже участвовать в коммуникациях.

---

# 13. DetachContactPointUseCase: входные данные

Лучше основной вариант делать по `binding_id`.

```python
@dataclass(frozen=True, slots=True)
class DetachContactPointCommand:
    binding_id: ContactPointBindingIdVO
```

---

# 14. DetachContactPointUseCase: результат

```python
@dataclass(frozen=True, slots=True)
class DetachContactPointResult:
    binding_id: ContactPointBindingIdVO
    contact_point_id: ContactPointIdVO

    binding_deleted: bool
    contact_point_left_orphan: bool
    contact_point_deleted: bool
```

Для MVP:

```text
contact_point_deleted = false
```

---

# 15. DetachContactPointUseCase: бизнес-логика

```text
1. Найти binding.
2. Если binding не найден — вернуть ошибку или идемпотентный success.
3. Получить contact_point_id из binding.
4. Удалить binding или пометить inactive.
5. Проверить, остались ли другие bindings у ContactPoint.
6. Если другие bindings есть — ContactPoint остается.
7. Если других bindings нет — ContactPoint становится orphan.
8. По умолчанию ContactPoint все равно остается.
9. Если detached binding был primary, выбрать другой contact point того же owner/type как primary.
10. Commit.
```

---

# 16. DetachContactPointUseCase: псевдокод

```python
class DetachContactPointUseCase:
    def __init__(
            self,
            uow: ContactPointUnitOfWorkProtocol,
            contact_point_lifecycle_policy: ContactPointLifecyclePolicy,
    ) -> None:
        self._uow = uow
        self._contact_point_lifecycle_policy = contact_point_lifecycle_policy

    async def execute(
            self,
            command: DetachContactPointCommand,
    ) -> DetachContactPointResult:
        async with self._uow:
            binding = await self._uow.bindings.get_by_id(command.binding_id)

            if binding is None:
                raise ContactPointBindingNotFoundError(command.binding_id)

            contact_point = await self._uow.contact_points.get_by_id(
                ContactPointIdVO(binding.contact_point_id.value)
            )

            if contact_point is None:
                raise ContactPointNotFoundError(binding.contact_point_id)

            was_primary = binding.is_primary
            owner = binding.owner

            await self._uow.bindings.delete(binding.id)

            has_other_bindings = await self._uow.bindings.exists_by_contact_point_id(
                contact_point_id=contact_point.id,
            )

            contact_point_deleted = False

            if was_primary:
                next_binding = await self._uow.bindings.find_next_binding_for_owner_and_type(
                    owner=owner,
                    contact_point_type=contact_point.type,
                )

                if next_binding is not None:
                    next_binding.is_primary = True
                    await self._uow.bindings.save(next_binding)

            can_delete_contact_point = await self._contact_point_lifecycle_policy.can_hard_delete(
                contact_point_id=contact_point.id,
                has_other_bindings=has_other_bindings,
            )

            if can_delete_contact_point:
                # Для MVP я бы НЕ делал это внутри Detach.
                # Лучше вынести в отдельный CleanupOrphanContactPointUseCase.
                pass

            await self._uow.commit()

        return DetachContactPointResult(
            binding_id=command.binding_id,
            contact_point_id=contact_point.id,
            binding_deleted=True,
            contact_point_left_orphan=not has_other_bindings,
            contact_point_deleted=contact_point_deleted,
        )
```

---

# 17. Soft detach

Лучше для CRM:

```text
is_active = false
detached_at = now()
```

Тогда `DetachContactPointUseCase` будет не удалять строку, а делать:

```text
binding.is_active = false
binding.detached_at = now()
```

Для CRM и истории это лучше.

---

# 18. Когда ContactPoint можно удалить

ContactPoint можно hard-delete только если одновременно выполнены все условия:

```text
1. У него нет активных bindings.
2. Он не участвовал в рассылках.
3. Он не участвовал в outbound_message.
4. По нему нет delivery_event.
5. По нему нет consent/opt-out записей.
6. По нему нет verification history, которую нужно хранить.
7. Он не находится в blacklist/suppression list.
8. Retention policy разрешает удаление.
```

То есть hard delete возможен только для технического мусора:

```text
импортировали ошибочный email,
не отправляли,
не привязывали,
не использовали,
сразу удалили.
```

---

# 19. Когда ContactPoint нельзя удалять

Нельзя удалять ContactPoint, если:

```text
1. Есть хотя бы один binding.
2. Есть история коммуникаций.
3. Есть BroadcastRecipient, который ссылался на ContactPoint.
4. Есть OutboundMessage, отправленный на этот ContactPoint.
5. Есть DeliveryEvent.
6. Есть unsubscribe / opt-out.
7. Есть верификация.
8. Это значение используется для duplicate detection.
```

Пример:

```text
Contact удалили телефон.
Но месяц назад на этот телефон была SMS-рассылка.

ContactPoint должен остаться,
иначе история рассылки потеряет адресата.
```

---

# 20. Правильная политика удаления

Я бы разделил операции:

```text
DetachContactPointUseCase
  удаляет только binding

CleanupOrphanContactPointUseCase
  отдельно удаляет orphan contact points, если это безопасно

ArchiveContactPointUseCase
  архивирует contact point, если удалить нельзя
```

Так безопаснее.

---

# 21. Матрица поведения

| Сценарий                                       | ContactPoint                   | Binding                     |
|------------------------------------------------|--------------------------------|-----------------------------|
| Новый phone/email для owner                    | создать                        | создать                     |
| Такой phone/email уже есть, но у другого owner | использовать существующий      | создать новый               |
| Такой phone/email уже есть у этого owner       | не создавать                   | не создавать                |
| Пользователь меняет phone/email                | создать/найти новый            | старый detach, новый attach |
| Пользователь удаляет phone/email с Contact     | оставить                       | удалить/deactivate          |
| ContactPoint больше ни к чему не привязан      | оставить orphan                | binding уже удален          |
| Orphan не использовался нигде                  | можно удалить cleanup job-ом   | —                           |
| ContactPoint участвовал в рассылке             | оставить навсегда/до retention | —                           |
| ContactPoint имеет opt-out                     | оставить suppression/consent   | —                           |

---

# 22. Как это должно работать с рассылками

Broadcast должен использовать `ContactPoint`, а не читать `phone/email` из Contact.

Пример:

```text
Broadcast SMS:
  -> выбрать ContactPoint where type = PHONE
  -> проверить consent
  -> проверить active
  -> создать BroadcastRecipient(contact_point_id)
  -> создать CommunicationRequest(contact_point_id)
```

Если список загружается CSV-файлом:

```text
phone,name,amount
+380671112233,Иван,15000
```

то лучше делать так:

```text
1. UpsertContactPointUseCase
2. создать ContactPoint, если его нет
3. создать BroadcastRecipient с contact_point_id
4. НЕ создавать CRM Contact автоматически
```

То есть импорт для рассылки не обязан создавать `Contact`, `Lead` или `Company`.

---

# 24. Repository protocols

## `contact_point/domain/contact_point/repository.py`

```python
from typing import Protocol


class ContactPointRepositoryProtocol(Protocol):
    async def get_by_id(
            self,
            contact_point_id: ContactPointIdVO,
    ) -> ContactPointEntity | None:
        ...

    async def get_by_type_and_hash(
            self,
            contact_point_type: ContactPointTypeVO,
            hash_value: str,
    ) -> ContactPointEntity | None:
        ...

    async def add(self, entity: ContactPointEntity) -> None:
        ...

    async def save(self, entity: ContactPointEntity) -> None:
        ...

    async def delete(self, contact_point_id: ContactPointIdVO) -> None:
        ...
```

---

## `contact_point/domain/binding/repository.py`

```python
from typing import Protocol


class ContactPointBindingRepositoryProtocol(Protocol):
    async def get_by_id(
            self,
            binding_id: ContactPointBindingIdVO,
    ) -> ContactPointBindingEntity | None:
        ...

    async def get_by_owner_and_contact_point(
            self,
            owner: OwnerContactPointBinding,
            contact_point_id: ContactPointIdVO,
    ) -> ContactPointBindingEntity | None:
        ...

    async def add(self, entity: ContactPointBindingEntity) -> None:
        ...

    async def save(self, entity: ContactPointBindingEntity) -> None:
        ...

    async def delete(
            self,
            binding_id: ContactPointBindingIdVO,
    ) -> None:
        ...

    async def exists_by_contact_point_id(
            self,
            contact_point_id: ContactPointIdVO,
    ) -> bool:
        ...

    async def unset_primary_for_owner_and_type(
            self,
            owner: OwnerContactPointBinding,
            contact_point_type: ContactPointTypeVO,
    ) -> None:
        ...

    async def find_next_binding_for_owner_and_type(
            self,
            owner: OwnerContactPointBinding,
            contact_point_type: ContactPointTypeVO,
    ) -> ContactPointBindingEntity | None:
        ...
```

---

# 25. Application ports

## OwnerResolverPort

Нужен, чтобы ContactPoint module не зависел напрямую от CRM/runtime_data.

```python
class OwnerResolverPort(Protocol):
    async def exists(
            self,
            owner: OwnerContactPointBinding,
    ) -> bool:
        ...
```

Реализации:

```text
CrmOwnerResolver
RuntimeDataOwnerResolver
```

---

## ContactPointUsageHistoryPort

Нужен, чтобы понять, можно ли удалить ContactPoint.

```python
class ContactPointUsageHistoryPort(Protocol):
    async def has_communication_history(
            self,
            contact_point_id: ContactPointIdVO,
    ) -> bool:
        ...

    async def has_broadcast_history(
            self,
            contact_point_id: ContactPointIdVO,
    ) -> bool:
        ...

    async def has_consent_history(
            self,
            contact_point_id: ContactPointIdVO,
    ) -> bool:
        ...
```

---

# 26. ContactPointLifecyclePolicy

```python
class ContactPointLifecyclePolicy:
    def __init__(
            self,
            usage_history: ContactPointUsageHistoryPort,
    ) -> None:
        self._usage_history = usage_history

    async def can_hard_delete(
            self,
            contact_point_id: ContactPointIdVO,
            has_other_bindings: bool,
    ) -> bool:
        if has_other_bindings:
            return False

        if await self._usage_history.has_communication_history(contact_point_id):
            return False

        if await self._usage_history.has_broadcast_history(contact_point_id):
            return False

        if await self._usage_history.has_consent_history(contact_point_id):
            return False

        return True
```

Но еще раз: я бы не вызывал hard delete внутри `DetachContactPointUseCase`. Лучше отдельным cleanup job.

---

# 27. Структура файлов

С учетом твоего текущего каркаса:

```text
src/
  modules/
    contact_point/
      domain/
        contact_point/
          entity.py
          repository.py

          value_object/
            contact_point_id.py
            contact_point_type.py

          service/
            contact_point_normalize_service.py
            contact_point_hash_service.py
            contact_point_lifecycle_policy.py

          error.py

        binding/
          entity.py
          repository.py

          value_object/
            contact_point_binding_id.py
            owner_binding.py

          error.py

      application/
        dto/
          attach_contact_point.py
          detach_contact_point.py
        
        command/
          attach_contact_point.py

        use_cases/
          attach_contact_point.py
          detach_contact_point.py
          cleanup_orphan_contact_point.py

      infrastructure/
        repository/
          contact_point_repository.py
          contact_point_binding_repository.py

        normalizer/
          phone_normalizer.py
          email_normalizer.py

        owner_resolver/
          runtime_data_owner_resolver.py
          crm_owner_resolver.py

      presentation/
        http/
          contact_point/
            requests/
            responses/
            controllers/

      depends/
        application.py
        infrastructure.py
```

Я бы переименовал файл:

```text
ovner_binding.py
```

в:

```text
owner_binding.py
```

Сейчас в имени есть опечатка.

---

# 28. DTO-файлы

## `application/dto/attach_contact_point.py`

```python
from dataclasses import dataclass

from src.modules.contact_point.domain.contact_point.value_object.contact_point_type import (
    ContactPointTypeVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class AttachContactPointCommand:
    owner_object_id: EntityIdVO
    owner_record_id: EntityIdVO
    contact_point_type: ContactPointTypeVO
    raw_value: str
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class AttachContactPointResult:
    contact_point_id: EntityIdVO
    binding_id: EntityIdVO
    contact_point_created: bool
    binding_created: bool
    already_attached: bool
```

---

## `application/dto/detach_contact_point.py`

```python
from dataclasses import dataclass

from src.modules.contact_point.domain.binding.value_object.contact_point_binding_id import (
    ContactPointBindingIdVO,
)
from src.modules.contact_point.domain.contact_point.value_object.contact_point_id import (
    ContactPointIdVO,
)


@dataclass(frozen=True, slots=True)
class DetachContactPointCommand:
    binding_id: ContactPointBindingIdVO


@dataclass(frozen=True, slots=True)
class DetachContactPointResult:
    binding_id: ContactPointBindingIdVO
    contact_point_id: ContactPointIdVO

    binding_deleted: bool
    contact_point_left_orphan: bool
    contact_point_deleted: bool
```

---

# 29. Нормализация и hash

## `contact_point_normalize_service.py`

```python
class ContactPointNormalizeService:
    def normalize(
            self,
            contact_point_type: ContactPointTypeVO,
            raw_value: str,
    ) -> str:
        if contact_point_type == ContactPointTypeVO.PHONE:
            return self._normalize_phone(raw_value)

        if contact_point_type == ContactPointTypeVO.EMAIL:
            return self._normalize_email(raw_value)

        raise UnsupportedContactPointTypeError(contact_point_type)

    def _normalize_email(self, value: str) -> str:
        return value.strip().lower()

    def _normalize_phone(self, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())

        if digits.startswith("0"):
            digits = f"38{digits}"

        if not digits.startswith("380"):
            raise InvalidPhoneError(value)

        return f"+{digits}"
```

---

## `contact_point_hash_service.py`

```python
import hashlib


class ContactPointHashService:
    def hash(self, normalized_value: str) -> str:
        return hashlib.sha256(
            normalized_value.encode("utf-8"),
        ).hexdigest()
```

В production лучше использовать tenant-specific salt или HMAC, чтобы hash нельзя было легко сопоставить с
телефоном/email.

---

# 30. Где должна быть транзакция

`AttachContactPointUseCase` и `DetachContactPointUseCase` должны выполняться через Unit of Work.

Repository и Unit of Work здесь уместны: Repository отделяет доменную модель от persistence-слоя, а Unit of Work
координирует изменения в рамках бизнес-транзакции. Это соответствует классическому описанию Repository как посредника
между domain и data mapping слоями, а Unit of Work — как механизма координации измененных объектов в
транзакции. ([martinfowler.com][1])

---

# 31. Минимальный UoW

```python
class ContactPointUnitOfWorkProtocol(Protocol):
    contact_points: ContactPointRepositoryProtocol
    bindings: ContactPointBindingRepositoryProtocol

    async def __aenter__(self) -> "ContactPointUnitOfWorkProtocol":
        ...

    async def __aexit__(self, exc_type, exc, tb) -> None:
        ...

    async def commit(self) -> None:
        ...

    async def rollback(self) -> None:
        ...
```

---

# 32. MVP порядок реализации

## Шаг 1

Доработать entities:

```text
ContactPointEntity
ContactPointBindingEntity
OwnerContactPointBinding
```

Минимально:

```text
created_at / updated_at в binding
is_active / detached_at — желательно
```

---

## Шаг 2

Добавить repository protocols:

```text
ContactPointRepositoryProtocol
ContactPointBindingRepositoryProtocol
```

---

## Шаг 3

Добавить services:

```text
ContactPointNormalizeService
ContactPointHashService
ContactPointLifecyclePolicy
```

---

## Шаг 4

Реализовать:

```text
AttachContactPointUseCase
DetachContactPointUseCase
```

---

## Шаг 5

Добавить DB constraints:

```sql
UNIQUE (contact_point_type, hash_value)

UNIQUE (
    owner_object_id,
    owner_record_id,
    contact_point_id
)
```

Если таблицы общие для всех tenant:

```sql
UNIQUE (tenant_id, contact_point_type, hash_value)

UNIQUE (
    tenant_id,
    owner_object_id,
    owner_record_id,
    contact_point_id
)
```

---

## Шаг 6

Добавить интеграцию с Broadcast:

```text
BroadcastRecipient.contact_point_id
```

Тогда рассылка будет ссылаться не просто на строку телефона/email, а на глобальный справочник.

---

# 33. Итоговая логика

```text
AttachContactPointUseCase
  если ContactPoint не существует:
      создать ContactPoint
      создать Binding

  если ContactPoint существует, но Binding нет:
      создать только Binding

  если ContactPoint существует и Binding существует:
      ничего не создавать, вернуть existing binding

DetachContactPointUseCase
  удалить/deactivate Binding
  ContactPoint оставить
  если ContactPoint orphan:
      не удалять сразу
      удалить только через отдельный cleanup policy, если нет истории
```

Главное правило:

```text
ContactPoint — это справочник и история контактируемости.
Binding — это связь справочника с конкретной CRM/runtime сущностью.
```

Поэтому удаление контакта с карточки Contact/Lead/Company — это удаление `Binding`, а не удаление `ContactPoint`.

[1]: https://martinfowler.com/eaaCatalog/repository.html?utm_source=chatgpt.com "Repository"
