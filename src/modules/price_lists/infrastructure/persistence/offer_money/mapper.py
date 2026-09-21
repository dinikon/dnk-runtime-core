from __future__ import annotations

from src.modules.currency.application.conversion.dto.converted_money import (
    ConvertedMoney,
)


def conversion_payload(result: ConvertedMoney | None) -> dict | None:
    """Portable public contract for a consumer-owned historical record."""
    if result is None:
        return None
    snapshot = result.conversion
    return {
        "original": {
            "amount": format(result.original.amount, "f"),
            "currency": str(result.original.currency),
        },
        "converted": {
            "amount": format(result.converted.amount, "f"),
            "currency": str(result.converted.currency),
        },
        "conversion": {
            "source_currency": str(snapshot.source_currency),
            "target_currency": str(snapshot.target_currency),
            "rate": format(snapshot.rate, "f"),
            "requested_date": snapshot.requested_date.isoformat(),
            "effective_date": snapshot.effective_date.isoformat(),
            "converted_at": snapshot.converted_at.isoformat(),
            "provider_code": snapshot.provider_code,
            "derivation": snapshot.derivation.value,
            "source_rate_ids": [str(i) for i in snapshot.source_rate_ids],
            "bridge_currency": (
                str(snapshot.bridge_currency) if snapshot.bridge_currency else None
            ),
            "policy_version": snapshot.policy_version,
            **(
                {
                    "purpose": snapshot.purpose,
                    "precision": snapshot.precision,
                    "rounding_mode": snapshot.rounding_mode,
                    "calculation_precision": snapshot.calculation_precision,
                    "minor_units": snapshot.minor_units,
                }
                if snapshot.purpose is not None
                else {}
            ),
        },
    }


__all__ = ["conversion_payload"]


def read_conversion(payload):
    """Read persisted revisions without looking up or reconstructing historical rates."""
    if payload is None:
        return None
    from datetime import date, datetime
    from decimal import Decimal
    from src.modules.shared.domain.value_object.money import Money
    from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
    from src.modules.shared.domain.value_object.entity_id import EntityIdVO
    from src.modules.currency.application.conversion.dto.conversion_snapshot import (
        ConversionSnapshot,
    )
    from src.modules.currency.domain.exchange_rate.value_object.rate_derivation import (
        RateDerivation,
    )

    s = payload["conversion"]
    return ConvertedMoney(
        Money(
            Decimal(payload["original"]["amount"]),
            CurrencyCodeVO(payload["original"]["currency"]),
        ),
        Money(
            Decimal(payload["converted"]["amount"]),
            CurrencyCodeVO(payload["converted"]["currency"]),
        ),
        ConversionSnapshot(
            CurrencyCodeVO(s["source_currency"]),
            CurrencyCodeVO(s["target_currency"]),
            Decimal(s["rate"]),
            date.fromisoformat(s["requested_date"]),
            date.fromisoformat(s["effective_date"]),
            datetime.fromisoformat(s["converted_at"]),
            s["provider_code"],
            RateDerivation(s["derivation"]),
            tuple(EntityIdVO.from_value(i) for i in s["source_rate_ids"]),
            CurrencyCodeVO(s["bridge_currency"]) if s.get("bridge_currency") else None,
            s["policy_version"],
            s.get("purpose"),
            s.get("precision"),
            s.get("rounding_mode"),
            s.get("calculation_precision"),
            s.get("minor_units"),
        ),
    )
