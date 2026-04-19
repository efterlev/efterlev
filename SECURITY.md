# Security Policy

Thank you for helping keep Efterlev and its users safe.

## Reporting a vulnerability

**Do not file security issues as public GitHub issues.**

Report security vulnerabilities privately by emailing the maintainer. Until a dedicated security address is established, please use GitHub's private vulnerability reporting feature:

👉 [Report a vulnerability](https://github.com/lhassa8/efterlev/security/advisories/new)

If private reporting is unavailable for any reason, you can also reach out through the contact information on the maintainer's GitHub profile.

## What to include

A good report typically includes:

- A description of the vulnerability and its potential impact
- Steps to reproduce (minimal proof-of-concept preferred)
- The version, commit, or configuration where you observed the issue
- Any suggested mitigation, if you have one

You do not need to have a fix ready. A clear description of the issue is enough.

## What to expect

- **Acknowledgment within 48 hours** of receipt (best-effort; Efterlev is currently maintained by one person).
- **A preliminary assessment within 7 days** classifying the severity and intended response.
- **Coordinated disclosure** on resolution, with credit to the reporter unless they prefer otherwise.

## Scope

This policy covers:

- The `efterlev` Python package and CLI
- The detector library shipped in this repository
- The MCP server exposed by Efterlev
- Official GitHub Actions or CI integrations (when they exist)

This policy does not cover:

- Vulnerabilities in third-party dependencies (please report those upstream; we will update our pinned versions once fixes are available)
- Issues in user-supplied detectors, plugins, or external extensions
- Operational security of any deployment running Efterlev

## Security commitments

Efterlev's security posture, including how we handle secrets, scan content, and LLM API interactions, is documented in [THREAT_MODEL.md](./THREAT_MODEL.md). Please read that document before reporting — it may answer questions about intended behavior.

Efterlev is Apache 2.0 licensed and provided without warranty. See [LICENSE](./LICENSE) for the full terms.

## Formal process

A more formal coordinated disclosure process, including a dedicated security contact address, PGP key, and SLA commitments, will be established before the v1.0 release. This stub will be replaced at that time.

---

*Last updated: repo creation. Future updates will be logged in [DECISIONS.md](./DECISIONS.md) under the `[threat-model]` tag.*
