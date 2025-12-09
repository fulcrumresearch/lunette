# Using Inspect AI

If you're using [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) for evaluations, Lunette integrates with one flag.

## Quick start

Add `--sandbox lunette` to your eval command:

```bash
inspect eval your_task.py --sandbox lunette
```

That's it. Your trajectories are now captured and uploaded to Lunette.

## Example task

Here's a minimal Inspect task configured for Lunette:

```python
--8<-- "examples/environment/inspect_task.py"
```

Run it:

```bash
inspect eval examples/environment/inspect_task.py --sandbox lunette --model anthropic/claude-haiku-4-5
```

## What gets captured

Lunette records:

- Every message (system, user, assistant, tool calls and results)
- Scores from your scorer
- Metadata you attach to samples
- The sandbox environment state (for later investigation)

## Running standard benchmarks

You can run existing Inspect benchmarks on Lunette. Here's SWE-bench:

```bash
inspect eval inspect_evals/swe_bench_verified_mini \
  --model openai/gpt-4o \
  --sandbox lunette \
  -T sandbox_type=lunette \
  -T build_docker_images=False
```

## Uploading existing logs

Have an Inspect `.eval` log file? Upload it directly:

```bash
lunette upload logs/2025-01-15_my-eval.eval
```

