# Announcement copy

Drafts for the launch sequence. Customize each before posting — replace the bracketed placeholders with current numbers.

## Hacker News (Show HN)

**Title:**

```
Show HN: Efterlev — open-source FedRAMP 20x scanner for Terraform
```

**Body (300 words max — HN penalizes long Show HN posts):**

```
Hi HN — I'm <BDFL handle>, and I just shipped Efterlev v0.1.0.

Efterlev is a repo-native, agent-first compliance scanner for FedRAMP 20x.
It scans your Terraform for KSI-level evidence, drafts FRMR-compatible
attestation JSON, and proposes code-level remediations. Runs locally,
Apache 2.0, no SaaS.

The pitch: a 100-person SaaS company gets told by a federal customer
"we'll buy if you're FedRAMP Moderate by next year." The team has three
options: hire a $250K consultant, buy a SaaS GRC platform priced for
larger orgs, or do it themselves with spreadsheets. Efterlev is the
fourth option — install in 60 seconds, scan your existing infra, get
real findings backed by a defensible provenance chain.

What's interesting technically:

- 30 deterministic detectors that emit Evidence records (content-
  addressed, source-line-pinned, reproducible). LLM agents reason over
  the evidence to classify KSI posture and draft attestations, but
  every claim cites the underlying evidence by ID.

- Per-run XML-fence nonces and post-generation citation validation
  prevent the agents from hallucinating evidence IDs the model didn't
  see.

- Runs anywhere: macOS / Linux / Windows / GovCloud EC2 with AWS
  Bedrock backend (so no egress to anthropic.com inside a FedRAMP
  boundary).

Pure OSS, no commercial tier ever. Sustained by maintainer time and
contributor goodwill — see GOVERNANCE.md for the model.

Docs: https://efterlev.com
Repo: https://github.com/efterlev/efterlev

Genuinely interested in feedback from anyone who's wrestled with first-
time FedRAMP authorization — what made it hard, what would have helped.
```

## Reddit — r/devops

**Title:** `Efterlev: open-source compliance scanner for Terraform (FedRAMP 20x focus)`

**Body:**

```
Hey r/devops — I've been building a tool for the "we just got told we
need FedRAMP" pain point and just shipped v0.1.0.

It's a CLI you run against your Terraform; produces a compliance gap
report grounded in actual `.tf` evidence, with proposed remediation
diffs the Remediation Agent generates. GitHub Action wraps it as a 3-
line CI integration.

Tech: Python 3.12, deterministic detectors over python-hcl2, three
LLM agents (Claude Opus + Sonnet) that reason over the evidence. Runs
in GovCloud via AWS Bedrock. Apache 2.0.

Not a substitute for a 3PAO; not trying to compete with Vanta on SOC
2; not multi-framework. Specifically the "first-time FedRAMP Moderate
SaaS" niche.

Curious if folks have wrestled with this — what worked, what didn't.

Docs: https://efterlev.com
```

## Reddit — r/govcloud, r/fednews

**Title:** `Open-source FedRAMP 20x compliance scanner — runs in GovCloud`

**Body:**

```
For folks pursuing FedRAMP authorization through the 20x track —

Efterlev is an open-source scanner that runs against your Terraform
and produces FRMR-compatible attestation JSON. Live in GovCloud via
the AWS Bedrock backend; the GovCloud deploy tutorial walks the IAM
policy, VPC endpoint, no-egress verification.

It does not produce ATOs. It produces drafts and findings; humans (and
your 3PAO) review and revise. The provenance chain is the defensible
answer when an assessor challenges a claim.

30 detectors at v0.1.0; 9 of 11 KSI themes covered. The 2 themes
unaddressed (AFR, KSO) are predominantly procedural and need Evidence
Manifests rather than IaC scanning.

Docs: https://efterlev.com  Repo: https://github.com/efterlev/efterlev

If you're in the middle of a 20x effort and want a maintainer-direct
feedback channel, ping me.
```

## Reddit — r/cybersecurity

**Title:** `Built an open-source compliance scanner with explicit Evidence-vs-Claims discipline (FedRAMP 20x)`

**Body:**

```
The thing that motivated this project: most compliance tooling that
uses LLMs blurs the line between "the scanner found this fact" and
"the LLM concluded this thing." Auditors hate that, justifiably.

Efterlev separates the two architecturally:

- Evidence is deterministic, scanner-derived, content-addressed.
  Reproducible byte-for-byte.
- Claims are LLM-reasoned. Carry a non-removable DRAFT marker. Every
  claim cites evidence by content-addressed ID. A post-generation
  validator rejects output citing IDs that weren't in the prompt's
  fences (per-run nonced) — so the agent can't make up IDs.

The provenance chain ('show me this sentence's chain back to a
Terraform line') is the architectural commitment. Took some thinking
to get right.

Apache 2.0. Pure OSS, no commercial tier.

https://efterlev.com
```

## LinkedIn

```
Today I'm releasing Efterlev — an open-source compliance scanner for
SaaS companies pursuing FedRAMP Moderate authorization through the 20x
track.

If you've been told "we need FedRAMP" and the next conversation involved
a $250K consulting engagement, this is the alternative entry point. Free,
local-first, runs against your Terraform, produces evidence your 3PAO can
actually use.

Apache 2.0 forever. Pure OSS, no commercial tier — sustained by
maintainer time and contributor goodwill. The choice not to monetize is
deliberate; the alignment of incentives matters when the tool's job is
to tell hard truths about your compliance posture.

Docs: https://efterlev.com

Genuinely interested in connecting with VPs of Engineering or DevSecOps
leads in the middle of a first-FedRAMP effort. Would love to learn what
made the path hard.
```

## dev.to / Medium long-form

**Title:** `Why we built Efterlev: an honest take on open-source compliance tooling`

```
[Long-form essay, ~1500 words. Outline:]

1. The problem: a $250K consulting industry serving a FedRAMP gold
   rush, with tooling priced for enterprises and incentives that
   reward inflated claims.

2. The architectural commitment that the rest of the project depends
   on: separating Evidence from Claims at the type level, with content-
   addressed provenance from generated text back to source lines.

3. Why pure OSS: every commercial-tier compliance tool has the same
   incentive problem (be useful enough to keep customers paying, not so
   useful that customers don't need them anymore). Pure OSS removes the
   incentive entirely. Whether it's sustainable on maintainer time
   alone is an open question — answered by whether contributors show up.

4. What we got wrong on the way here: started closed-source, pivoted
   to open per a market reality check that flagged Paramify's Phase 2
   authorization moment as the closing-window signal.

5. What's next: 30 detectors today, 100+ over time as contributors
   show up. Drift detection. CMMC 2.0 overlay. Real PR creation from
   the Remediation Agent.

6. How to get involved: Discussions, good-first-issues, the detector
   contract.

End with a specific call to action — a concrete "here's what we'd
love help with."
```

## Blog post on docs site

Same content as dev.to but hosted at `efterlev.com/blog/why-efterlev`. The docs site's MkDocs setup can grow a blog plugin (`mkdocs-material`'s blog plugin is built-in) when this lands.

## Slack communities

Slack posts are different from public-feed posts. Tone: "I just shipped this, might be relevant to people doing FedRAMP-adjacent work." Link to docs. Invite questions. **Do not** paste the marketing copy.

```
Hey folks — I just shipped Efterlev, an open-source FedRAMP 20x
scanner. Repo-native (you run it against your Terraform, no SaaS),
Apache 2.0, runs in GovCloud via Bedrock.

Genuinely interested in feedback from anyone wrestling with FedRAMP-
adjacent work. Docs at https://efterlev.com — happy to answer
questions here or in GitHub Discussions.
```

## Customization checklist

Before posting any of the above:

- [ ] Replace `<BDFL handle>` with the real handle.
- [ ] Update any phase-2-authorization or detector-count references with current numbers.
- [ ] Confirm `efterlev.com` resolves and the docs site is live.
- [ ] Have at least one trusted reader skim each post before submission.
- [ ] Schedule per the runbook timing (HN at hour 0; Reddit/LinkedIn at hour 4; Slack at hour 8; blog Day 1).
