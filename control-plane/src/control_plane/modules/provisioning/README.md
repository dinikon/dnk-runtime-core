# Provisioning

Owns asynchronous `ProvisioningOperation`, idempotent commands, retries,
desired/actual state, transactional outbox and orchestration of tenant create,
suspend, resume and deletion. It never creates a distributed database
transaction with Runtime Core.
