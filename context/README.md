# Context Pack

Use this directory to hand the demo to another model, CI harness, or blog
automation.

## Goal

Demonstrate hermetic agents with a small, deterministic e2e proof:

- Code and test writers get the same spec.
- Each writer has a disjoint input manifest.
- The code writer cannot see tests.
- The test writer cannot see implementation.
- QA can inspect both outputs plus a hidden oracle and assign blame backward.

## Main Commands

```bash
./scripts/run_hermetic_agents_demo.sh
python3 scripts/hermetic_agents_demo.py --self-test
bazelisk test //:hermetic_agents_e2e_test
crabbox job run hermetic-agents
```

## Publishing

- Repo: `https://github.com/zozo123/hermetic-agents-demo`
- Pages: `https://zozo123.github.io/hermetic-agents-demo/`
- Pages source: `docs/`
- Workflow: `.github/workflows/pages.yml`

## Crabbox Path

`.crabbox.yaml` defines one job:

```bash
crabbox job run hermetic-agents
```

It uses `provider: islo`, runs `./scripts/run_hermetic_agents_demo.sh`, requires
`docs/metrics/hermetic-agents-e2e.json`, and downloads the JSON/Markdown proof
under `.crabbox/proofs/`.

## Important Result

The seeded disagreement is a bad generated test expectation. QA assigns blame to
`test_writer`, proving that hidden/generated tests are not automatically truth.
