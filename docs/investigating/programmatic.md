# Programmatic Investigations

Run investigations directly from your code using the Lunette SDK. This enables automated analysis pipelines, CI/CD integration, and custom tooling.

## Basic Usage

```python
--8<-- "examples/programmatic_investigation.py"
```

Run it:

```bash
export RUN_ID="your-run-id"
python examples/programmatic_investigation.py
```

## Analysis Plans

Lunette provides three built-in plan types, each with a structured output schema. Import them from `lunette.analysis`:

```python
from lunette.analysis import GradingPlan, IssueDetectionPlan, BottleneckPlan
```

### Grading

Score trajectories on custom dimensions:

```python
from lunette.analysis import GradingPlan

plan = GradingPlan(
    name="efficiency-grade",
    prompt="Grade this trajectory on computational efficiency. Consider time complexity and resource usage.",
)
```

**Output schema** (`GradeResult`):

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Name of the score dimension |
| `score` | `float` | Score between 0.0 and 1.0 |
| `explanation` | `str` | Reasoning for the score |

### Issue Detection

Find problems in agent behavior or environment:

```python
from lunette.analysis import IssueDetectionPlan

plan = IssueDetectionPlan(
    name="find-bugs",
    prompt="Identify any bugs or errors in the agent's approach.",
)
```

**Output schema** (`IssueResult`):

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Short issue title |
| `role` | `IssueRole` | `"agent"` or `"environment"` |
| `description` | `str` | Detailed description |
| `confidence` | `float` | Confidence between 0.0 and 1.0 |
| `proof` | `str` | Evidence supporting the issue |
| `message_ids` | `list[int]` | Related message indices |

### Bottleneck Analysis

Identify the primary limiting factor:

```python
from lunette.analysis import BottleneckPlan

plan = BottleneckPlan(
    name="find-bottleneck",
    prompt="What was the main obstacle preventing success?",
)
```

**Output schema** (`BottleneckResult`):

| Field | Type | Description |
|-------|------|-------------|
| `bottleneck` | `str` | Description of the bottleneck |
| `root_cause_message_id` | `int \| None` | Message index where it occurred |

## Filtering Trajectories

Use `TrajectoryFilters` to select which trajectories to analyze:

```python
from lunette.analysis import GradingPlan, TrajectoryFilters

plan = GradingPlan(
    name="failed-only",
    prompt="Why did this trajectory fail?",
    trajectory_filters=TrajectoryFilters(
        score={"op": "lt", "value": 0.5},  # only failing trajectories
    ),
)
```

Available filters:

| Filter | Type | Description |
|--------|------|-------------|
| `task` | `str` | Filter by task name |
| `sample` | `str \| list[str]` | Filter by sample ID(s) |
| `score` | `float \| ScoreFilter` | Exact score or comparison (`lt`, `gt`, `lte`, `gte`, `eq`) |

## Options

The `investigate` method accepts additional parameters:

```python
results = await client.investigate(
    run_id="your-run-id",
    plan=plan,
    limit=10,        # max trajectories to analyze
    batch_size=5,    # concurrent analysis agents
)
```

## Working with Results

The `InvestigationResults` object contains:

```python
results.run_id              # ID of the investigation run
results.source_run_id       # ID of the original run analyzed
results.trajectory_count    # number of trajectories analyzed
results.results             # list of TrajectoryResult objects
```

Each `TrajectoryResult` contains:

```python
result.original_trajectory_id       # ID of the analyzed trajectory
result.investigation_trajectory_id  # ID of the investigation trajectory
result.result_type                  # e.g., "grading", "issue_detection"
result.data                         # dict with the structured output
```

## Plan Configuration

All plan types support these optional fields:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Name for the analysis |
| `prompt` | `str` | Instructions for the investigator |
| `trajectory_filters` | `TrajectoryFilters` | Which trajectories to analyze |
| `model` | `str` | LLM model override |
| `max_turns` | `int` | Maximum investigator turns |
| `enable_sandbox` | `bool` | Enable sandbox access |
| `enable_claim_evaluator` | `bool` | Enable claim verification |

## YAML Serialization

Plans can be serialized to/from YAML for configuration files:

```python
from lunette.analysis import GradingPlan, parse_analysis_plan

# serialize
plan = GradingPlan(name="my-plan", prompt="Grade quality.")
yaml_str = plan.to_yaml()
plan.to_yaml_file("plan.yaml")

# deserialize
plan = parse_analysis_plan(yaml_str)
```

Example YAML:

```yaml
kind: grading
name: code-quality
prompt: |
  Grade this trajectory on code quality.
  Consider readability, maintainability, and best practices.
trajectory_filters:
  score:
    op: lt
    value: 1.0
```
