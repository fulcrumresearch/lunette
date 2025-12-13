# Grading Code with an Agentic Judge

Pass/fail tests miss a lot. An agent might pass tests with hacky code, or write excellent code that fails on a minor edge case. This walkthrough shows how to build a proper evaluation pipeline: run a coding agent, then have an agentic judge evaluate the code in the same environment.

## The setup

We'll:
1. Run a coding agent on a set of problems
2. Capture trajectories with full environment access
3. Launch an agentic judge that reviews the code *in the original sandbox*

The judge can actually run the code, test edge cases, inspect the implementation—not just read the transcript.

## Step 1: Run your coding agent

Here's a simple coding task. The agent gets a problem and writes Python to solve it:

```python
--8<-- "examples/coding_eval.py"
```

Run the script:

```bash
python coding_eval.py
```

## Step 2: Grade the run

Go to [lunette.dev](https://lunette.dev), find your run, and click "Grade". Use this prompt:

```
Review the code in each trajectory's sandbox.

## Process

1. First, read the code the agent wrote:
   - cat /workspace/*.py to see all files

2. Run the code to verify it works:
   - Import the module and test basic functionality
   - Test edge cases (empty inputs, large inputs, special characters, etc.)

3. Analyze code quality:
   - Is it correct? Does it handle all cases?
   - Is it readable? Good variable names, clear logic?
   - Is it efficient? Reasonable time/space complexity?
   - Is it robust? Input validation, error handling?
   - Does it follow Python conventions? PEP 8, type hints, docstrings?

## Output

For each file, provide:

**Correctness** (0-10):
- Score and explanation
- Any bugs found (with reproduction steps)

**Readability** (0-10):
- Score and explanation
- Specific issues (line numbers if relevant)

**Efficiency** (0-10):
- Time complexity analysis
- Space complexity analysis
- Any obvious optimizations missed

**Robustness** (0-10):
- Edge cases tested and results
- Missing error handling

**Style** (0-10):
- PEP 8 compliance
- Documentation quality
- Type hints presence

**Overall Score**: weighted average (correctness 30%, others 17.5% each)

**Summary**: 2-3 sentences on the code quality

**Critical Issues**: Any bugs or security issues that must be fixed
```

## What the judge does

Unlike a static analysis tool, the agentic judge actually *uses* the sandbox:

1. **Reads the code** — `cat /workspace/fizzbuzz.py`
2. **Tests it** — Runs the function with various inputs
3. **Probes edge cases** — What happens with `fizzbuzz(0)`? `fizzbuzz(-5)`?
4. **Checks behavior** — Does `is_palindrome("A man, a plan, a canal: Panama")` work?
5. **Reports findings** — With concrete evidence from execution

## Example output

```
Trajectory: fizzbuzz
File: /workspace/fizzbuzz.py

Correctness: 9/10
- Basic functionality works correctly
- Edge case issue: fizzbuzz(0) returns [1] instead of []
- Reproduction: python3 -c "from fizzbuzz import fizzbuzz; print(fizzbuzz(0))"

Readability: 8/10
- Clear logic with good structure
- Variable names are descriptive
- Missing docstring for the function

Efficiency: 10/10
- O(n) time complexity, optimal
- O(n) space for output list, necessary

Robustness: 6/10
- No input validation for negative numbers
- No type checking on input
- fizzbuzz("hello") raises unclear TypeError

Style: 7/10
- Follows PEP 8
- No type hints
- No docstring

Overall Score: 8.0/10

Summary: Solid implementation with correct core logic. Main issues are
missing edge case handling for n<=0 and lack of documentation.

Critical Issues:
- fizzbuzz(0) returns incorrect result
- No input validation could cause confusing errors
```

## Why this matters

Traditional evals give you "70% pass rate"—but that hides crucial information:

- Did the agent write maintainable code?
- Would you want this code in production?
- What patterns does the agent consistently miss?

With an agentic judge, you get rich signal on *how* your agent codes, not just whether it passes tests. You can track improvements over time, identify systematic weaknesses, and build better agents.
