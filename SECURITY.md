# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Prefer one of:

1. GitHub Security Advisories for this repository (Private vulnerability reporting), or
2. Email the maintainers listed in the repository profile / `CODEOWNERS` if present.

Include:

- Description of the issue and impact
- Reproduction steps or proof of concept
- Affected versions / commit SHA
- Any suggested remediation

We aim to acknowledge reports within 7 days and provide a remediation timeline after triage.

## Scope

In scope: the `githubbench-delta` package, CI configuration, and default sample configs.

Out of scope: third-party model provider APIs, user-supplied datasets, and secrets stored in local `.env` files.
