# Inventory Module

## Purpose

`inventory` exposes product and product category management for tenant-scoped sellable physical goods. It uses runtime
schema tables described by `schema_registry` seed metadata instead of static ORM product tables.

## Public Functionality

- create, read, list, update and delete products
- create, read, list, update and delete product categories
- get runtime field descriptions for products and categories

## Main Flows / Use Cases

- `CreateProduct`, `GetProduct`, `ListProducts`, `UpdateProduct`, `DeleteProduct`
- `DescribeProductFields`
- `CreateCategory`, `GetCategory`, `ListCategories`, `UpdateCategory`, `DeleteCategory`
- `DescribeCategoryFields`

## Domain Model

- `ProductEntity`
    - `id`
    - timestamps
    - required tenant-local `sku`
    - required `product_name`
    - optional `description`
    - optional `category_id`
- `CategoryEntity`
    - `id`
    - timestamps
    - required `name`
    - optional `parent_category_id` self-reference for category trees

## Infrastructure / Persistence

- Inventory repositories live under `inventory/infrastructure`
- repositories resolve runtime object descriptors for `product` and `product_category`
- writes and reads go through `runtime_data` gateways using the active request `UnitOfWork`
- HTTP payloads do not accept `tenant_id`; controllers read it from request context and pass it through inventory
  commands, queries, use cases and repository calls
- wiring stays tenant-agnostic and does not bind repositories to a tenant
- category deletion is protected by runtime foreign keys when products or child categories still reference it

## Presentation / Entry Points

All inventory routes live under `/api/inventory`:

- `POST /products`
- `POST /products/fields`
- `GET /products`
- `GET /products/{product_id}`
- `PUT /products/{product_id}`
- `DELETE /products/{product_id}`
- `POST /categories`
- `POST /categories/fields`
- `GET /categories`
- `GET /categories/{category_id}`
- `PUT /categories/{category_id}`
- `DELETE /categories/{category_id}`

All routes require authenticated request context.

## Dependencies On Other Modules

- uses `shared` authentication, request context, identifiers, time and UoW dependencies
- uses `schema_registry` to resolve runtime object descriptors and field descriptions
- uses `runtime_data` for tenant-scoped CRUD over runtime tables

## Tests Covering This Module

- inventory seed/planning tests
- inventory domain/service tests
- inventory runtime repository tests
- inventory controller error mapping tests

## Related

- [HTTP API](../interfaces/http-api.md)
- [Runtime schema](../data/runtime-schema.md)
- [Domain models](../data/domain-models.md)
- [Test map](../quality/test-map.md)

## Source Of Truth

- `src/modules/inventory/domain/product/entity.py`
- `src/modules/inventory/domain/category/entity.py`
- `src/modules/inventory/infrastructure/product_runtime_repository.py`
- `src/modules/inventory/infrastructure/category_runtime_repository.py`
