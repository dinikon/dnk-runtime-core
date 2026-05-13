"""Имена runtime-таблиц communication bounded context."""

_CONNECTOR = "communication_provider_connector"
_MESSAGE_TYPE = "communication_provider_message_type"
_CONNECTION = "communication_provider_connection"
_TEMPLATE = "communication_message_template"
_TEMPLATE_VERSION = "communication_template_version"
_REQUEST = "communication_request"
_OUTBOUND = "communication_outbound_message"
_ATTEMPT = "communication_delivery_attempt"
_EVENT = "communication_delivery_event"

__all__ = [
    "_ATTEMPT",
    "_CONNECTION",
    "_CONNECTOR",
    "_EVENT",
    "_MESSAGE_TYPE",
    "_OUTBOUND",
    "_REQUEST",
    "_TEMPLATE",
    "_TEMPLATE_VERSION",
]
