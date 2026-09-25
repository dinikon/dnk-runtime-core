from dataclasses import replace
from src.modules.contact_points.domain.binding.entity import ContactPointBinding
from src.modules.contact_points.domain.binding.error import (
    InvalidContactPointBindingError,
)
from src.modules.contact_points.domain.binding.repository import (
    ContactPointBindingRepositoryProtocol,
)
from src.modules.contact_points.domain.contact_point.error import (
    InvalidContactPointError,
)
from src.modules.contact_points.domain.contact_point.service import ContactPointResolver
from src.modules.contact_points.domain.contact_point.value_object.value import (
    ContactPointType,
)
from src.modules.contact_points.domain.label.repository import (
    ContactPointLabelRepositoryProtocol,
)
from src.modules.shared.domain.time import ClockPort


class ContactPointBindingService:
    """Синхронизирует массивы одного заблокированного владельца без commit."""

    def __init__(
        self,
        resolver: ContactPointResolver,
        bindings: ContactPointBindingRepositoryProtocol,
        labels: ContactPointLabelRepositoryProtocol,
        clock: ClockPort,
    ):
        self.resolver, self.bindings, self.labels, self.clock = (
            resolver,
            bindings,
            labels,
            clock,
        )

    async def sync(self, tenant_id, actor_id, target, phones, emails):
        """Валидирует весь ввод, переиспользует точки и сохраняет связи атомарно."""
        groups = (
            (ContactPointType.PHONE, "phones", phones),
            (ContactPointType.EMAIL, "emails", emails),
        )
        if phones is None and emails is None:
            return
        current = await self.bindings.list_for_targets(tenant_id, (target,))
        old = {row.binding.id: row for row in current}
        labels = {
            label.id: label
            for label in await self.labels.list(tenant_id, for_share=True)
        }
        prepared = []
        keep = []
        seen_ids = set()
        for kind, array, drafts in groups:
            if drafts is None:
                keep.extend(row.binding for row in current if row.point.type == kind)
                continue
            seen_values = set()
            for index, draft in enumerate(drafts):
                previous = old.get(draft.binding_id) if draft.binding_id else None
                if draft.binding_id and (
                    previous is None
                    or previous.point.type != kind
                    or draft.binding_id in seen_ids
                ):
                    raise InvalidContactPointBindingError(
                        "Связь не принадлежит этому списку объекта или повторяется.",
                        array,
                        index,
                        "binding_id",
                    )
                if draft.binding_id:
                    seen_ids.add(draft.binding_id)
                try:
                    normalized = self.resolver.normalize(
                        kind, draft.value, draft.country_code
                    )
                except InvalidContactPointError as exc:
                    raise InvalidContactPointBindingError(
                        str(exc), array, index, exc.field
                    ) from exc
                if normalized.value in seen_values:
                    raise InvalidContactPointBindingError(
                        "Это значение уже добавлено.", array, index
                    )
                seen_values.add(normalized.value)
                if draft.label_id:
                    label = labels.get(draft.label_id)
                    unchanged = (
                        previous is not None
                        and previous.binding.label_id == draft.label_id
                    )
                    if (
                        label is None
                        or label.type != kind
                        or (not label.is_active and not unchanged)
                    ):
                        raise InvalidContactPointBindingError(
                            "Выберите действующую подпись этого типа.",
                            array,
                            index,
                            "label_id",
                        )
                prepared.append((kind, index, draft, normalized, previous))
        # Stable order prevents two multi-value requests from taking unique-index locks in opposite order.
        points = {}
        for kind, index, draft, normalized, previous in sorted(
            prepared, key=lambda item: (item[0].value, item[3].value.value)
        ):
            points[(kind, normalized.value)] = await self.resolver.resolve(
                tenant_id, actor_id, draft.candidate_point_id, kind, normalized
            )
        now = self.clock.now()
        for kind, index, draft, normalized, previous in prepared:
            point = points[(kind, normalized.value)]
            if previous:
                binding = replace(previous.binding)
                binding.update(
                    point_id=point.id,
                    label_id=draft.label_id,
                    position=index,
                    actor_id=actor_id,
                    now=now,
                )
            else:
                binding = ContactPointBinding.create(
                    binding_id=draft.candidate_binding_id,
                    point_id=point.id,
                    target=target,
                    label_id=draft.label_id,
                    position=index,
                    actor_id=actor_id,
                    now=now,
                )
            keep.append(binding)
        before = {row.binding.id: row.binding for row in current}
        after = {binding.id: binding for binding in keep}
        if before != after:
            await self.bindings.replace_for_target(tenant_id, target, tuple(keep))


__all__ = ["ContactPointBindingService"]
