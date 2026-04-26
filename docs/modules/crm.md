# CRM Module

## Purpose

`crm` currently exposes a small contact management surface. At this stage the module is intentionally narrow: it handles
only contacts.

## Public Functionality

- create contact
- get contact model description
- get contact by id
- list contacts with pagination
- update contact name
- delete contact

## Main Flows / Use Cases

- `CreateContact`
- `DescribeContactFields`
- `GetContact`
- `ListContacts`
- `UpdateContact`
- `DeleteContact`

## Domain Model

- `ContactEntity`
    - `id`
    - timestamps
    - `ContactNameVO` with last, first and middle name

## Infrastructure / Persistence

- CRM repositories live under `crm/infrastructure`
- current persistence integrates with shared database layer and authenticated request context
- HTTP payloads do not accept `tenant_id`; controllers read it from request context and pass it through CRM commands,
  queries, use cases and repository calls
- wiring stays tenant-agnostic and does not bind repositories to a tenant

## Presentation / Entry Points

All current CRM routes live under `/api/crm/contacts`:

- `POST /`
- `POST /fields`
- `GET /`
- `GET /{contact_id}`
- `PUT /{contact_id}`
- `DELETE /{contact_id}`

All routes currently require authenticated request context.

## Dependencies On Other Modules

- uses `shared` authentication dependency and request context
- relies on request-domain tenant resolution rather than its own tenant bootstrap logic

## Tests Covering This Module

- contact endpoint tests
- contact use case tests
- CRM domain tests

## Related

- [HTTP API](../interfaces/http-api.md)
- [Domain models](../data/domain-models.md)
- [Request lifecycle](../architecture/request-lifecycle.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/crm/presentation/http/router.py`
- `src/modules/crm/domain/contact/entity.py`
- `src/modules/crm/domain/contact/service.py`
- `src/modules/crm/application/contact/use_case/`
