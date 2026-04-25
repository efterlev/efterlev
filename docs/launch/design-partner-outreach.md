# Design-partner outreach

Five email templates for ICP-A targets. Sent on Day 2 of launch week per the runbook. Customize each with a current-news hook ("just saw your CEO interviewed about the federal pipeline...") before sending.

## Why these emails matter

The 2026-04-22 v1 scope-lock specifically chose archetype-only design over a named-prospect commitment. The decision was rationally defensible (no prospect → no premature schema-surface commitment) but accepted as debt: we'd need a real first user to validate Evidence Manifest YAML shape, POA&M reviewer fields, Gap Agent edge cases, etc.

Day 2 of launch is when that debt comes due. The emails are the first move.

## What good design partners look like for v0.2

- **50–200 engineer SaaS** with a committed federal customer deal contingent on FedRAMP Moderate authorization.
- **Mostly Terraform** infrastructure (so v0.1.0's detector library covers them).
- **DevSecOps lead or platform engineer** running the FedRAMP push, NOT a dedicated compliance team.
- **Active in the FedRAMP 20x process** — Phase 3 applicants ideally, current Phase 2 participants still useful.
- **Willing to share sanitized Terraform** in exchange for direct maintainer support.

## The shared body

The five emails share a body. Customization is in the opening paragraph (the hook) and the close (the specific ask).

```
[OPENING HOOK — see per-target customization below]

I'm <BDFL name>, the maintainer of Efterlev. We just shipped v0.1.0
(Apache 2.0, https://efterlev.com) — an open-source FedRAMP 20x
scanner that runs locally against your Terraform.

We deliberately don't have a sales team or a paid tier. The pitch is
just: install in 60 seconds, scan your existing infra, see whether
the output is useful before any commitment.

What's specifically valuable to a [their company]-shaped team:

- 30 detectors covering 9 of 11 FRMR-Moderate KSI themes. AWS-Terraform-
  focused at v0.1.0; the gaps are honest about procedural-only KSIs.
- Local-first. Your Terraform never leaves your machine. The agents
  call Claude (anthropic-direct or AWS Bedrock), with secret redaction
  before egress.
- Evidence chain that survives 3PAO scrutiny — every assertion in the
  attestation traces back to a Terraform line.

What we'd value from you:

- 30 minutes of feedback on your first scan, captured as a private
  GitHub Discussion thread (happy to do it as a video call if easier).
- Permission to use your high-level usage (anonymized, with your
  approval before publication) as a v0.2 case study.

What you'd get from us:

- Direct maintainer attention. v0.2 schema choices (Evidence Manifest
  YAML, POA&M reviewer fields, Gap Agent edge cases) will be informed
  by your specific feedback.
- A heads-up channel for breaking changes — anything pre-1.0 may shift
  in response to your input.
- Recognition in `CONTRIBUTORS.md` if you want, anonymous if you don't.

[CLOSE — per-target customization below]
```

## Per-target customization

Replace the bracketed names + companies + hooks with real-world targets. **Five targets is a deliberate constraint** — more dilutes the maintainer's ability to respond fast; fewer reduces the chance any one will land.

### Target 1: A SaaS announced as a FedRAMP 20x Phase 3 applicant

**Opening hook draft:**

```
Saw [Company] in the most recent FedRAMP 20x cohort announcement —
congrats on the application going in. The 30-day Phase 2 timeline gives
me hope Phase 3 might compress similarly for follow-on applicants.
```

**Close:**

```
If a 60-second install + a real scan against your fedramp-boundary
Terraform sounds useful at this stage, I'd love to hear back. No reply
needed if not — but if you do try it and it's useless, I'd value the
"this didn't work for X reason" data point too.

— <BDFL name>
```

### Target 2: A SaaS in the middle of a Phase 2 cohort

**Opening hook draft:**

```
[Company] was named in the Phase 2 Moderate cohort announcement back in
December — assuming you're mid-package-prep right now and probably busy.
```

**Close:**

```
You're closer to authorization than the rest of the field, which means
your feedback is the most valuable. If Efterlev would be useful to you
at this stage I'd love to hear back; if not, even a "we already use X
for this and Efterlev would have to do Y to displace it" would be
concretely actionable.

— <BDFL name>
```

### Target 3: A Y Combinator B2B SaaS that recently announced gov-pipeline traction

**Opening hook draft:**

```
[Company]'s [recent funding announcement / Show HN / TechCrunch piece]
mentioned federal customers in the pipeline. The "we got the deal but
need FedRAMP first" moment is exactly the use case Efterlev was built
for.
```

**Close:**

```
30-minute conversation? Worst case you tell me Efterlev is missing
something important; best case you save 6 months of FedRAMP timeline.

— <BDFL name>
```

### Target 4: A defense-adjacent SaaS pursuing CMMC 2.0 or DoD IL

**Opening hook draft:**

```
Efterlev's primary focus is FedRAMP 20x, but the architecture extends
to CMMC 2.0 (same 800-171 base, different overlay) and DoD Impact
Levels. If [Company] is chasing CMMC alongside or instead of FedRAMP
Moderate, the v0.1.0 detector library is ~70% directly applicable
plus some IL-specific gaps.
```

**Close:**

```
CMMC overlay is currently v1.5+ on the roadmap, but a credible design
partner accelerates that. Would [Company] be interested in being that
partner? If so, your feedback shapes which CMMC controls land first.

— <BDFL name>
```

### Target 5: A SaaS recently mentioned in DevSecOps tooling discussions

**Opening hook draft:**

```
Saw [Company]'s [recent blog post / OSS contribution / conference talk]
on [topic]. Your team's attention to deployment-pipeline security
suggests you'd evaluate Efterlev technically rather than as a
checkbox-compliance tool, which is the only way the project gets honest
feedback.
```

**Close:**

```
If a thoughtful technical evaluation is something you have an hour for,
that's the highest-value form of feedback I could get pre-v0.2. Even a
detailed teardown of why it's *not* the right fit is concrete signal.

— <BDFL name>
```

## How to track replies

Private spreadsheet (or a private GitHub Project) with columns:

- Target name
- Date sent
- Reply received? (yes/no/unsubscribed)
- Reply substance (positive/neutral/negative)
- Follow-up scheduled?
- Notes

**Don't follow up sooner than 5 business days.** A second email inside a week reads as pressure; the whole pitch is the absence of pressure.

If a target replies positively, move them to a private GitHub Discussion and start the v0.2 feedback-integration window per the launch plan's Phase C.4. Schedule a 30-minute call only after they've actually run a scan and have specific things to discuss.

## What if all five say no?

The project survives. Five outreach attempts is a small sample; the public launch produces its own surface area for inbound design partners. Continue the runbook; revisit outreach in 30 days with a refreshed target list informed by what we've learned about who's adopting.

If all five say no AND inbound after 30 days is also silent, that's the launch-plan-30-day-gates "yellow" state from `DECISIONS.md` 2026-04-23 — pause and reassess messaging before building more product.
