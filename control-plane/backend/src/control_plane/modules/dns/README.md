# DNS

Owns DNS record intent, provider account references, reconciliation and the
`DnsProviderPort`. Cloudflare is the first adapter. Provider tokens are never
stored in application tables; only `secret_ref` values are persisted.
