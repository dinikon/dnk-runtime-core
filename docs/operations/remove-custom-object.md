# Custom Object Module Removal

This release removes the `custom_object` backend module and its generic record CRUD API without replacement.

## Deployment

1. Deploy the release normally; no database reset, schema diff or data migration is required.
2. Keep existing custom object metadata, `c_*` physical tables and their records unchanged.
3. Consumers must stop calling `/api/console/custom-objects/records/*`.

## Verification

- `/api/console/custom-objects/records/*` is absent from OpenAPI and representative requests return `404`.
- `/api/console/config/objects/list`, `/create`, `/delete` and `/schema` remain in OpenAPI.
- `ObjectKind.CUSTOM` remains `custom`, and schema config continues to create and preserve `c_*` objects.
