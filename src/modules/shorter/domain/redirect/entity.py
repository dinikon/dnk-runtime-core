from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .value_object import (
    RedirectIdVO,
    RedirectTargetUrlVO,
    RedirectUtmParametersVO,
)


@dataclass(slots=True)
class RedirectEntity:
    id: RedirectIdVO
    created_at: datetime
    updated_at: datetime
    target_url: RedirectTargetUrlVO
    utm_parameters: RedirectUtmParametersVO
    is_override: bool
    is_append: bool

    @classmethod
    def create(
        cls,
        *,
        target_url: RedirectTargetUrlVO,
        utm_parameters: RedirectUtmParametersVO,
        is_override: bool,
        is_append: bool,
        created_at: datetime,
    ) -> "RedirectEntity":
        return cls(
            id=RedirectIdVO.new(),
            created_at=created_at,
            updated_at=created_at,
            target_url=target_url,
            utm_parameters=utm_parameters,
            is_override=is_override,
            is_append=is_append,
        )

    def update(
        self,
        *,
        target_url: RedirectTargetUrlVO,
        utm_parameters: RedirectUtmParametersVO,
        is_override: bool,
        is_append: bool,
        updated_at: datetime,
    ) -> None:
        self.target_url = target_url
        self.utm_parameters = utm_parameters
        self.is_override = is_override
        self.is_append = is_append
        self.updated_at = updated_at

    def resolve_target_url(
        self,
        *,
        short_link_query_params: dict[str, object] | None = None,
    ) -> str:
        parsed_target = urlparse(self.target_url.value)
        target_query_params = dict(
            parse_qsl(parsed_target.query, keep_blank_values=True)
        )
        resolved_query_params = dict(target_query_params)
        resolved_query_params.update(self.utm_parameters.as_dict())

        incoming_utm_params = RedirectUtmParametersVO.from_mapping(
            short_link_query_params
        ).as_dict()

        if self.is_override:
            for key, value in incoming_utm_params.items():
                if key in resolved_query_params:
                    resolved_query_params[key] = value

        if self.is_append:
            for key, value in incoming_utm_params.items():
                if key not in resolved_query_params:
                    resolved_query_params[key] = value

        return urlunparse(
            parsed_target._replace(query=urlencode(resolved_query_params))
        )


__all__ = ["RedirectEntity"]
