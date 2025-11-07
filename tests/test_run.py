"""Tests for the Run model and client integration."""

import pytest
from lunette.models.messages import AssistantMessage, UserMessage
from lunette.models.run import Run
from lunette.models.trajectory import ScalarScore, Trajectory


def test_run_creation():
    """Test creating a Run with trajectories."""
    run = Run(
        id="test-run-1",
        task="test-task",
        model="claude-sonnet-4",
        trajectories=[
            Trajectory(
                sample="1",
                messages=[
                    UserMessage(position=0, content="Test message"),
                    AssistantMessage(position=1, content="Test response"),
                ],
                scores={"main": ScalarScore(value=1.0)},
            ),
        ],
    )

    assert run.id == "test-run-1"
    assert run.task == "test-task"
    assert run.model == "claude-sonnet-4"
    assert len(run.trajectories) == 1
    assert run.trajectories[0].sample == "1"


def test_run_validation_empty_trajectories():
    """Test that Run can be created with empty trajectories (validation happens in client)."""
    run = Run(
        id="test-run-1",
        task="test-task",
        model="claude-sonnet-4",
        trajectories=[],
    )

    assert len(run.trajectories) == 0


def test_run_serialization():
    """Test Run serialization to dict."""
    run = Run(
        id="test-run-1",
        task="test-task",
        model="claude-sonnet-4",
        trajectories=[
            Trajectory(
                sample="1",
                messages=[
                    UserMessage(position=0, content="Test message"),
                ],
                scores={"main": ScalarScore(value=1.0)},
            ),
        ],
    )

    run_dict = run.model_dump()

    assert run_dict["id"] == "test-run-1"
    assert run_dict["task"] == "test-task"
    assert run_dict["model"] == "claude-sonnet-4"
    assert len(run_dict["trajectories"]) == 1
    assert run_dict["trajectories"][0]["sample"] == "1"
    # Verify run_id is not in the trajectory
    assert "run_id" not in run_dict["trajectories"][0]


def test_trajectory_without_task_model_or_run_id():
    """Test that client Trajectory is pure execution trace without relational fields."""
    trajectory = Trajectory(
        sample="1",
        messages=[
            UserMessage(position=0, content="Test message"),
        ],
        scores={"main": ScalarScore(value=1.0)},
        metadata={},
    )

    # Verify relational fields are not in the model
    assert not hasattr(trajectory, "task")
    assert not hasattr(trajectory, "model")
    assert not hasattr(trajectory, "run_id")

    # Verify serialization doesn't include relational fields
    traj_dict = trajectory.model_dump()
    assert "task" not in traj_dict
    assert "model" not in traj_dict
    assert "run_id" not in traj_dict
    # Verify it has the execution trace fields
    assert traj_dict["sample"] == "1"
    assert "messages" in traj_dict
    assert "scores" in traj_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
