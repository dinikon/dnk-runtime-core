# Control Plane cabinet

The cabinet will be a separate Vue 3 + TypeScript application following the
existing DNK console conventions: Vite, Vue Router, Pinia, TanStack Query,
Axios, vee-validate/Zod and shared shadcn-vue style primitives.

Planned feature layout:

```text
src/
├── app/                 # bootstrap, router, session and providers
├── layouts/             # auth and cabinet shells
├── modules/
│   ├── auth/
│   ├── profile/
│   ├── customers/
│   ├── tenants/
│   ├── domains/
│   ├── installations/
│   ├── operations/
│   ├── billing/
│   └── platform-settings/
├── components/ui/
└── shared/
```

The first usable slice is login, current profile, tenant list, tenant create,
tenant detail/status and owner transfer. Domain and installation screens are
added after their backend workflows are reliable.

This directory intentionally has no `package.json` yet. The frontend bootstrap
phase must decide whether to keep a completely independent Node workspace or
join the existing root `frontends` workspace while preserving a separate build
artifact.
