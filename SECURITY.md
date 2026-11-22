# Security policy

## Supported versions

Only the default branch (`main`) is supported. Fixes land there.

## Reporting a vulnerability

Report it privately through GitHub: open the repository's Security tab and choose "Report a vulnerability". Do not open a public issue or pull request for it.

Include what you found, the request or steps that show it, and the commit you tested. This is a local tool that binds `127.0.0.1` only, so the most useful reports concern the request guards (Host and Origin checks, body cap, static file allowlist), input validation and the SQLite storage.
