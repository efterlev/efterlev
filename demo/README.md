# demo/

This directory contains `govnotes`, a synthetic gov-adjacent SaaS used as the demo target for
Efterlev's scanners and agents.

`govnotes` is pinned here as a git submodule pointing at
[`lhassa8/govnotes-demo`](https://github.com/lhassa8/govnotes-demo), locked to a specific
known-good commit. To populate it on a fresh clone:

```bash
git submodule update --init demo/govnotes
```

See [`docs/dual_horizon_plan.md`](../docs/dual_horizon_plan.md) §2.2 for what `govnotes`
contains and why — deliberate compliance gaps the Gap Agent flags, ambiguous cases a
reviewer has to disambiguate, and the good-neighbor pattern the detectors should avoid
false-flagging.
