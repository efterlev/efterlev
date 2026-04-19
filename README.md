# Efterlev

**Open-source compliance automation for SaaS companies pursuing their first FedRAMP Moderate authorization.**

Scans your Terraform and application code for compliance-relevant evidence. Drafts OSCAL artifacts for your 3PAO. Proposes code-level remediations you can apply today. Runs locally — no SaaS, no telemetry, no procurement cycle.

Built for the VP Eng or DevSecOps lead whose CEO just told them "we need FedRAMP" and who needs to know, by Monday, where they actually stand.

Pronounced "EF-ter-lev." From Swedish *efterlevnad* (compliance).

```bash
pipx install efterlev
cd your-repo
efterlev init --profile fedramp-moderate
efterlev scan
```

Efterlev's current focus is SaaS companies pursuing their first FedRAMP Moderate authorization. Defense contractors pursuing CMMC 2.0 or DoD IL are a v1.5+ expansion; platform teams at larger gov-contractors are v2+. See [docs/icp.md](./docs/icp.md) for the full user profile and what that means for what Efterlev does and doesn't do.

---

## What it does

- **Scans** Terraform and application source for evidence of FedRAMP controls
- **Drafts** OSCAL System Security Plan narratives grounded in that evidence
- **Proposes** code-level remediation diffs for detected gaps
- **Emits** standards-compliant OSCAL artifacts consumable by tools like RegScale's OSCAL Hub
- **Traces** every generated claim back to the source line that produced it

Everything runs locally. The only outbound network call is to your configured LLM endpoint for reasoning tasks (narrative drafting, remediation proposals). Scanner output is deterministic and offline.

## What it doesn't do

- It does not produce an Authorization to Operate. Humans and 3PAOs do that.
- It does not certify compliance. It produces drafts that accelerate the human review cycle.
- It does not guarantee generated narratives are correct. Every LLM-generated artifact is marked "DRAFT — requires human review."
- It does not cover SOC 2, ISO 27001, HIPAA, or GDPR. Other tools serve those well; see [COMPETITIVE_LANDSCAPE.md](./COMPETITIVE_LANDSCAPE.md) for the landscape.
- It does not scan live cloud infrastructure yet. v1.

See [LIMITATIONS.md](./LIMITATIONS.md) for the honest full accounting.

---

## Why it exists

A 100-person SaaS company just got told by its biggest prospect: "we'll buy, but only if you're FedRAMP Moderate by next year."

The team looks at each other. Nobody has done this before. They google it and find:

- Consulting engagements starting at $250K
- SaaS compliance platforms that cover SOC 2 beautifully but treat FedRAMP as a footnote
- Enterprise GRC tooling priced for the wrong scale
- Spreadsheets, Word templates, and a NIST document family that runs to thousands of pages

What they actually need is something that reads their Terraform and tells them, in their own language, what's wrong and how to fix it. Something a single engineer can install on a Tuesday and show results at Wednesday's standup. Something whose output is concrete enough that their 3PAO can use it — and whose claims are honest enough that the 3PAO won't throw it out.

Efterlev is that tool. It runs where the engineer already is (the repo, the CLI, the CI pipeline). It produces OSCAL because the FedRAMP PMO's RFC-0024 mandates machine-readable packages by September 2026. It refuses to overclaim because 3PAOs don't trust tools that do.

It's also deliberately deep rather than broad. FedRAMP Moderate first; DoD IL and CMMC 2.0 on the v1 roadmap. Not SOC 2, not ISO 27001, not HIPAA — there are tools that serve those well, and our value is depth in gov-grade frameworks, not breadth across every compliance acronym.

Add [COMPETITIVE_LANDSCAPE.md](./COMPETITIVE_LANDSCAPE.md) to see where Efterlev fits among existing tools.

---

## Quickstart

### Install

```bash
pipx install efterlev
```

Requires Python 3.12+. `uv` is used internally but not required for end users.

### Configure

```bash
cd path/to/your-repo
efterlev init --profile fedramp-moderate
```

This creates a `.efterlev/` directory for the local provenance store, downloads the FedRAMP Moderate OSCAL baseline, and writes a config file.

You'll need an Anthropic API key for the generative agents (narrative drafting, remediation). Set `ANTHROPIC_API_KEY` in your environment or configure it in `.efterlev/config.toml`.

### Scan

```bash
efterlev scan
```

Runs all applicable detectors against your Terraform and source. Produces findings with full provenance. Scanner-only — no LLM calls, no network except to load local OSCAL catalogs.

### Analyze

```bash
efterlev agent gap
```

The Gap Agent classifies each control as implemented, partially implemented, not implemented, or not applicable, given the evidence collected. Writes a human-readable HTML report to `out/gap_report.html`.

### Draft SSP narrative

```bash
efterlev agent document --control SC-28
```

The Documentation Agent drafts System Security Plan narrative for a control, grounded in its evidence. Output is an OSCAL-aligned draft; every sentence cites the evidence that supports it.

### Propose remediation

```bash
efterlev agent remediate --control SC-28
```

The Remediation Agent proposes a code-level diff to address a gap. Review the diff, then apply it yourself or hand it to Claude Code.

### Walk the provenance

```bash
efterlev provenance show <claim_id>
```

Every generated claim traces back to the evidence that produced it and the source line that produced that. If the chain doesn't resolve, the claim is weak.

---

## Current coverage

### Input sources (v0)

Efterlev v0 scans **Terraform and OpenTofu** source files (`.tf`). It does not scan CloudFormation, AWS CDK, Pulumi, Kubernetes manifests, or live cloud infrastructure. Each of those is on the v1 roadmap below.

If your FedRAMP boundary is Terraform-primary, Efterlev works for you today. If you're deep in CloudFormation or CDK, hold off — v1 is not far.

### FedRAMP Moderate controls (v0)

| Control | Name | Source |
|---|---|---|
| SC-28 | Protection of Information at Rest | Terraform/OpenTofu (S3, RDS, EBS) |
| SC-8 | Transmission Confidentiality | Terraform/OpenTofu (ALB, TLS) |
| SC-13 | Cryptographic Protection | Terraform/OpenTofu, source |
| IA-2 | Identification & Authentication | Terraform/OpenTofu (IAM, MFA) |
| AU-2 + AU-12 | Event Logging & Audit Generation | Terraform/OpenTofu (CloudTrail) |
| CP-9 | System Backup | Terraform/OpenTofu (RDS, S3 versioning) |

Every detector's `README.md` inside `src/efterlev/detectors/` names what it proves and what it does not prove. Read those before trusting a finding.

### On the roadmap

Expansion happens along two axes in parallel: **input sources** (what Efterlev can scan) and **control coverage** (what it can find). Source-type expansion matters more for adoption; control-count expansion matters more for depth.

- **Month 1:** Terraform Plan JSON support (scans resolved plans including computed values); OpenTofu declared as first-class alongside Terraform
- **Month 1–2:** +15 detectors for Terraform (AC-*, AU-3, CM-2/6, SI-*, SC-7); AWS Bedrock as a second LLM backend for FedRAMP-authorized deployments (GovCloud)
- **Month 2:** CloudFormation and AWS CDK support (CDK compiles to CloudFormation; one parser covers both)
- **Month 3:** First external contributor detector merged; Kubernetes manifests + Helm (network policies, pod security, RBAC — different control set, high value)
- **Month 4:** GitHub Action for PR-level compliance checks; Pulumi support
- **Month 5:** CMMC 2.0 overlay
- **Month 6:** Drift Agent — watches a repo over time, flags regressions in evidenced controls
- **v1.5+:** Runtime cloud API scanning (different threat model, needs its own design pass)

See [docs/dual_horizon_plan.md](./docs/dual_horizon_plan.md) for the full roadmap.

---

## How it works

Three concepts. Everything else is implementation detail.

**Detectors** read source material (Terraform plans, app code, CI configs) and emit deterministic evidence. They are the moat: a community-contributable library where each detector is a self-contained folder.

**Primitives** are typed, MCP-exposed functions that represent agent-legible capabilities — scan, map, generate, validate. ~15–25 of them, small and stable. Both our own agents and external agents (your own Claude Code session, for instance) can call them.

**Agents** compose primitives to accomplish a reasoning task: classifying gap status, drafting SSP narrative, proposing remediation. Each agent has a system prompt you can read in the repo and a typed output artifact you can audit.

Every step emits a provenance record. The provenance store is a content-addressed, append-only graph — scanner output is evidence, agent output is a claim derived from that evidence, and you can walk the chain from any generated sentence back to the Terraform line that produced it.

The architectural bet: evidence before claims, provenance always, OSCAL as output not internal model. See [docs/architecture.md](./docs/architecture.md) for details.

---

## Integrating with Claude Code

Efterlev exposes its primitives via an MCP server. Point any Claude Code session at it and Claude can discover and call every primitive directly.

```bash
efterlev mcp serve
```

In your Claude Code settings, add the server. Claude can now scan your repo, walk provenance, draft narratives, or propose remediations as part of a broader coding session — the same capabilities Efterlev's own agents use, available to yours.

This also means: if you want to build a compliance workflow Efterlev doesn't ship, you don't need to fork Efterlev. Write your own agent against the MCP interface.

---

## Project status

**v0.1** — hackathon release. Six detectors, three agents, FedRAMP Moderate only, AWS + Terraform only. Usable for gap analysis and draft SSP generation; not yet a production workflow.

**Stable surface:** primitive interface, detector contract, provenance model, OSCAL output formats. These are designed to not break.

**Changing surface:** detector content (as we add more), agent system prompts (as we tune them), CLI ergonomics (as we hear from users).

---

## Contributing

We want contributors. The detector library is designed to make the common contribution — "here's a new control I can detect" — a self-contained folder that doesn't touch the rest of the codebase.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the five-minute path from `git clone` to running tests, and the hour path from idea to open PR.

Good first issues are labeled `good first issue` on GitHub. The most valuable contributions right now are new detectors for controls on the roadmap.

---

## Governance

Benevolent-dictator model during v0–v1 (the author), with an explicit commitment to move to a technical steering committee at 10 active contributors. See [DECISIONS.md](./DECISIONS.md) for the governance record and [CONTRIBUTING.md](./CONTRIBUTING.md) for how maintainer status works.

This project may be donated to a neutral foundation (OpenSSF, Linux Foundation, CNCF) at maturity if contributor diversity warrants. That decision is not made and not time-boxed.

---

## License and security

Apache 2.0. See [LICENSE](./LICENSE).

Security issues: see [SECURITY.md](./SECURITY.md) for the coordinated disclosure process.

Threat model for Efterlev itself: [THREAT_MODEL.md](./THREAT_MODEL.md).

---

## Credits

Efterlev was bootstrapped in a 4-day hackathon using [Claude Code](https://claude.com/claude-code). The architecture commits to keeping Claude Code (and other MCP-capable agents) as first-class integration partners — that's what "agent-first" means here, structurally, not as marketing.

Built on [compliance-trestle](https://github.com/IBM/compliance-trestle) for OSCAL processing, and on the OSCAL baselines published by [FedRAMP Automation](https://github.com/GSA/fedramp-automation) and [NIST](https://github.com/usnistgov/OSCAL). Those projects make this one possible.

---

## Documentation

- [docs/icp.md](./docs/icp.md) — the Ideal Customer Profile: who Efterlev is for, how we decide what to build
- [docs/dual_horizon_plan.md](./docs/dual_horizon_plan.md) — full plan and roadmap
- [docs/architecture.md](./docs/architecture.md) — deeper architectural detail
- [LIMITATIONS.md](./LIMITATIONS.md) — what Efterlev does and doesn't do
- [THREAT_MODEL.md](./THREAT_MODEL.md) — security posture
- [COMPETITIVE_LANDSCAPE.md](./COMPETITIVE_LANDSCAPE.md) — honest positioning against Comp AI, RegScale OSCAL Hub, and others
- [DECISIONS.md](./DECISIONS.md) — architectural decision log
- [CONTRIBUTING.md](./CONTRIBUTING.md) — contributor onboarding
