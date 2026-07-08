# Hermetic Agents Demo

Standalone demo for "hermetic agents": separate code-writing and test-writing
agents work from the same spec, but cannot see each other's outputs. A QA agent
gets both outputs plus an oracle and assigns blame when implementation and tests
disagree.

Target repo:

```text
https://github.com/zozo123/hermetic-agents-demo
```

Target Pages site:

```text
https://zozo123.github.io/hermetic-agents-demo/
```

## Run Locally

```bash
./scripts/run_hermetic_agents_demo.sh
python3 scripts/hermetic_agents_demo.py --self-test
bazelisk test //:hermetic_agents_e2e_test
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
- `docs/`: GitHub Pages static site.
- `context/`: short handoff pack for other models and harnesses.
