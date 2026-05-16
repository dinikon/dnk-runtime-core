# CRM Module

## Purpose

`crm` currently exposes contact and company management surfaces backed by runtime schema tables.

## Public Functionality

- create contact
- get contact model description
- get contact by id
- list contacts with pagination
- update contact name
- delete contact
- create company
- get company model description
- get company by id
- list companies with pagination
- update company legal name
- delete company

## Main Flows / Use Cases

- `CreateContact`
- `DescribeContactFields`
- `GetContact`
- `ListContacts`
- `UpdateContact`
- `DeleteContact`
- `CreateCompany`
- `DescribeCompanyFields`
- `GetCompany`
- `ListCompanies`
- `UpdateCompany`
- `DeleteCompany`

## Domain Model

- `ContactEntity`
    - `id` as `ContactIdVO`
    - timestamps
    - `ContactNameVO` with last, first and middle name
- `CompanyEntity`
    - `id` as `CompanyIdVO`
    - timestamps
    - required `legal_name`

## Infrastructure / Persistence

- CRM repositories live under `crm/infrastructure`
- current persistence integrates with shared database layer and authenticated request context
- HTTP payloads do not accept `tenant_id`; controllers read it from request context and pass it through CRM commands,
  queries, use cases and repository calls
- internally that tenant scope is `EntityIdVO`; contact/company ids are concrete domain value objects and are converted
  to UUIDs only at HTTP/runtime-data boundaries
- wiring stays tenant-agnostic and does not bind repositories to a tenant

## Presentation / Entry Points

Contact routes live under `/api/crm/contacts`:

- `POST /`
- `POST /fields`
- `GET /`
- `GET /{contact_id}`
- `PUT /{contact_id}`
- `DELETE /{contact_id}`

Company routes live under `/api/crm/companies`:

- `POST /`
- `POST /fields`
- `GET /`
- `GET /{company_id}`
- `PUT /{company_id}`
- `DELETE /{company_id}`

All routes currently require authenticated request context.

## Dependencies On Other Modules

- uses `shared` authentication dependency and request context
- relies on request-domain tenant resolution rather than its own tenant bootstrap logic

## Tests Covering This Module

- contact endpoint tests
- contact use case tests
- company endpoint tests
- company use case tests
- CRM domain tests

## Related

- [HTTP API](../interfaces/http-api.md)
- [Domain models](../data/domain-models.md)
- [Request lifecycle](../architecture/request-lifecycle.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/crm/presentation/http/router.py`
- `src/modules/crm/domain/contact/entity.py`
- `src/modules/crm/domain/company/entity.py`
- `src/modules/crm/application/contact/use_case/`
- `src/modules/crm/application/company/use_case/`
