from src.modules.external_fulfillment.domain.draft_basis_snapshot import (
    SupplierFulfillmentOfferSnapshot,
    SupplierFulfillmentPlanBasisSnapshot,
    SupplierFulfillmentSourceSnapshot,
)
from src.modules.external_fulfillment.domain.entity.supplier_fulfillment_line import (
    SupplierFulfillmentLine,
)
from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
    SupplierFulfillmentBasisMismatchError,
)
from src.modules.external_fulfillment.domain.value_object.line_binding import (
    SupplierFulfillmentLineBindingVO,
)


class SupplierFulfillmentDraftPolicy:
    """Сопоставляет выбранные распределения с одним источником и его предложениями."""

    @staticmethod
    def build_lines(
        *,
        basis: SupplierFulfillmentPlanBasisSnapshot,
        source: SupplierFulfillmentSourceSnapshot,
        offers: tuple[SupplierFulfillmentOfferSnapshot, ...],
        line_bindings: tuple[SupplierFulfillmentLineBindingVO, ...],
    ) -> tuple[SupplierFulfillmentLine, ...]:
        """Проверяет полное основание и создаёт строку на каждое выбранное распределение."""
        if (
            not isinstance(basis, SupplierFulfillmentPlanBasisSnapshot)
            or not isinstance(source, SupplierFulfillmentSourceSnapshot)
            or not isinstance(offers, tuple)
            or not isinstance(line_bindings, tuple)
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Нужны снимки плана и источника, tuple предложений и привязок строк."
            )
        basis.ensure_valid()
        source.ensure_valid()
        if not source.is_active or not source.supports_dropship:
            raise SupplierFulfillmentBasisMismatchError(
                "Для черновика нужен активный источник с режимом DROPSHIP."
            )
        by_offer = {}
        for offer in offers:
            if not isinstance(offer, SupplierFulfillmentOfferSnapshot):
                raise InvalidSupplierFulfillmentValueError("Нужны снимки предложений.")
            offer.ensure_valid()
            if offer.id in by_offer:
                raise SupplierFulfillmentBasisMismatchError(
                    "Снимок предложения повторяется."
                )
            by_offer[offer.id] = offer
        if set(by_offer) != {row.supplier_offer_id for row in basis.allocations}:
            raise SupplierFulfillmentBasisMismatchError(
                "Нужны ровно предложения выбранных распределений."
            )
        by_allocation = {}
        line_ids = set()
        for binding in line_bindings:
            if not isinstance(binding, SupplierFulfillmentLineBindingVO):
                raise InvalidSupplierFulfillmentValueError(
                    "Нужны номинальные привязки строк."
                )
            if binding.allocation_id in by_allocation or binding.line_id in line_ids:
                raise SupplierFulfillmentBasisMismatchError(
                    "Распределение и ID строки должны быть уникальны в привязках."
                )
            by_allocation[binding.allocation_id] = binding.line_id
            line_ids.add(binding.line_id)
        if set(by_allocation) != {row.allocation_id for row in basis.allocations}:
            raise SupplierFulfillmentBasisMismatchError(
                "Каждому выбранному распределению нужна ровно одна строка."
            )
        lines = []
        for row in basis.allocations:
            offer = by_offer[row.supplier_offer_id]
            if (
                row.supplier_source_id != source.id
                or offer.supplier != source.supplier
                or (offer.source_id is not None and offer.source_id != source.id)
                or not offer.is_active
                or offer.inventory_item_id != row.inventory_item_id
                or offer.base_uom != row.base_uom
            ):
                raise SupplierFulfillmentBasisMismatchError(
                    "Все строки требуют один источник, активные предложения его поставщика и совпадающие товары и единицы."
                )
            lines.append(
                SupplierFulfillmentLine.create(
                    identifier=by_allocation[row.allocation_id],
                    fulfillment_allocation_id=row.allocation_id,
                    inventory_item_id=row.inventory_item_id,
                    supplier_offer_id=row.supplier_offer_id,
                    base_uom=row.base_uom,
                    requested_quantity=row.quantity,
                    quoted_price=row.quoted_price,
                )
            )
        return tuple(lines)
