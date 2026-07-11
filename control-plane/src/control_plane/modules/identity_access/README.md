# Identity and access

Owns global `UserAccount`, `UserProfile`, verified email/phone contacts,
`ExternalIdentity`, OTP challenges, browser sessions, recovery and account
linking. It is independent from Runtime Core's tenant-local identity module.

Delivery is delegated to `notifications` ports. Email/phone normalization,
challenge hashing, TTL, attempt limits, rate limits and re-authentication rules
remain owned here.
