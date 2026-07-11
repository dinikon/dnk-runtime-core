# Backend modules

| Module | Ownership |
| --- | --- |
| `identity_access` | Global user, profile, contacts, OTP, sessions and OAuth identities |
| `system_profile` | Singleton public platform profile and non-secret global settings |
| `customers` | Customer organization/legal profile and customer membership |
| `tenancy` | Tenant, membership, roles, owner transfer and lifecycle |
| `installations` | Runtime installations, environments, credentials, heartbeat and placement |
| `provisioning` | Long-running operations, commands, desired/actual state and outbox |
| `domains` | Domain binding, verification and TLS lifecycle |
| `dns` | DNS provider ports, Cloudflare adapter and DNS reconciliation |
| `cluster_management` | Kubernetes targets, routes, certificates and state snapshots |
| `notifications` | Email and Telegram delivery adapters |
| `billing` | Plans, subscriptions and invoices; scheduled after the core MVP |
| `audit` | Immutable security and administrative audit trail |
| `shared` | Narrow technical kernel without business aggregates |

Each directory currently contains a responsibility note. Domain/application/
infrastructure/presentation packages are added when the first use case of that
bounded context is implemented, avoiding empty placeholder layers.
