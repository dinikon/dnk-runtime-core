"""Pure rules for editing the two views of contact/company membership."""

from src.modules.crm.domain.company.value_object import CompanyIdVO
from src.modules.shared.domain.domain_error import DomainError, EntityIdTypeError


class DuplicateCrmLinkError(DomainError):
    """A selection contains the same related object more than once."""


class CrmLinksChangedError(DomainError):
    """The original membership no longer matches the current membership."""


class InvalidCrmLinksError(DomainError):
    """An update is missing its original membership snapshot."""


def company_selection(ids):
    return _selection(ids, CompanyIdVO)


def contact_selection(ids):
    from src.modules.crm.domain.contact.value_object import ContactIdVO

    return _selection(ids, ContactIdVO)


def _selection(ids, identifier_type):
    values = tuple(ids)
    if any(type(identifier) is not identifier_type for identifier in values):
        raise EntityIdTypeError("CRM links require the correct typed identifiers.")
    if len(set(values)) != len(values):
        raise DuplicateCrmLinkError("Объект уже добавлен в список связей.")
    return frozenset(values)


def ensure_current_links(current, expected):
    if expected is None:
        raise InvalidCrmLinksError("Для обновления необходим исходный список связей.")
    if frozenset(current) != frozenset(expected):
        raise CrmLinksChangedError(
            "Связи изменились. Загрузите актуальную карточку перед сохранением."
        )


class CompanyContactLinksPolicy:
    """Validate reverse membership without loading or persisting aggregates."""

    @staticmethod
    def changes(*, current, expected, requested):
        desired = contact_selection(requested)
        if expected is not None:
            contact_selection(expected)
        ensure_current_links(current, expected)
        previous = contact_selection(current)
        return desired - previous, previous - desired

    @staticmethod
    def ensure_available(*, available, requested, expected):
        from src.modules.crm.domain.contact.error import ContactNotFoundError

        if set(expected) - set(available):
            raise CrmLinksChangedError(
                "Связанный контакт был удалён. Загрузите карточку заново."
            )
        if set(requested) - set(available):
            raise ContactNotFoundError("Contact not found.")
