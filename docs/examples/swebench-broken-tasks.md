# Finding Broken Tasks in SWE-bench

SWE-bench Verified is the most popular software engineering benchmark, but it still contains unsolvable tasks—broken tests, missing dependencies, ambiguous specifications. This walkthrough shows how to find them.

## 1. Run SWE-bench

```bash
lunette eval swebench --model anthropic/claude-sonnet-4 --limit 50
```

This runs 50 SWE-bench instances with full environment capture. Every command, file change, and model response is recorded.

## 2. View your results

Go to [lunette.dev](https://lunette.dev) and find your run. You'll see:

- Pass/fail for each task
- The full trajectory (what the agent did)
- Access to the original environment

## 3. Launch an investigation

Click "Investigate", select the default prompt, and then set it off. The investigator agent will:

1. Read what the agent tried to do
2. Access the sandbox environment
3. Run commands to test hypotheses
4. Report what it finds

Check in a few minutes and you'll see issues start coming in.
