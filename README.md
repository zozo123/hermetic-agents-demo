# Hermetic Agents Demo

A deterministic demo of "hermetic agents" for people designing agent coding
pipelines: scripted code-writing and test-writing roles work from the same spec
but cannot see each other's outputs, and a QA arbiter with a hidden oracle
assigns blame when they disagree.

Live page: https://zozo123.github.io/hermetic-agents-demo/ · By
[Yossi Eliaz](https://yossieliaz.netlify.app/)

Status: deterministic demo (July 2026). The roles are scripted in
`scripts/hermetic_agents_demo.py`; no language model is called, and the wrong
test expectation is seeded on purpose.

## Run Locally

```bash
./scripts/run_hermetic_agents_demo.sh
python3 scripts/hermetic_agents_demo.py --self-test
bazelisk test //:hermetic_agents_e2e_test
```

Run the same proof through [Crabbox](https://github.com/openclaw/crabbox) on a
delegated islo.dev sandbox:

```bash
export CRABBOX_ISLO_API_KEY=ak_...
crabbox job run hermetic-agents
```

Or without the job wrapper:

```bash
crabbox run --provider islo \
  --require-artifact docs/metrics/hermetic-agents-e2e.json \
  --download docs/metrics/hermetic-agents-e2e.json=.crabbox/proofs/hermetic-agents-e2e.json \
  --shell './scripts/run_hermetic_agents_demo.sh'
```

The demo writes:

- `docs/metrics/hermetic-agents-e2e.json`
- `docs/metrics/hermetic-agents-e2e.md`

## What It Proves

- The code writer receives only `spec/problem.md` and `guides/code-writer.md`.
- The test writer receives only `spec/problem.md` and `guides/test-writer.md`.
- Manifest leak checks prove neither side received forbidden artifacts.
- QA can blame the test writer when a generated test contradicts the spec.
- The same proof runs locally, in Bazel, and in GitHub Actions.

## Key Files

- `scripts/hermetic_agents_demo.py`: deterministic coder/tester/QA harness.
- `scripts/run_hermetic_agents_demo.sh`: local runner that updates Pages metrics.
- `BUILD.bazel`: Bazel e2e target.
- `.crabbox.yaml`: Crabbox/Islo job that requires and downloads the proof JSON.
- `docs/`: GitHub Pages static site.
- `context/`: short handoff pack for other models and harnesses.
