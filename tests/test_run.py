"""Tests for the Run model and client integration."""

import pytest
from lunette.models.run import Run
from lunette.models.trajectory import Trajectory, ScalarScore
from lunette.models.messages import UserMessage, AssistantMessage


def test_run_creation():
    """Test creating a Run with trajectories."""
    run = Run(
        run_id="test-run-1",
        task="test-task",
        model="claude-sonnet-4",
        trajectories=[
            Trajectory(
                run_id="test-run-1",
                sample="1",
                messages=[
                    UserMessage(position=0, content="Test message"),
                    AssistantMessage(position=1, content="Test response"),
                ],
                scores={"main": ScalarScore(value=1.0)},
                metadata={},
            ),
        ],
    )

    assert run.run_id == "test-run-1"
    assert run.task == "test-task"
    assert run.model == "claude-sonnet-4"
    assert len(run.trajectories) == 1
    assert run.trajectories[0].run_id == "test-run-1"


def test_run_validation_empty_trajectories():
    """Test that Run can be created with empty trajectories (validation happens in client)."""
    run = Run(
        run_id="test-run-1",
        task="test-task",
        model="claude-sonnet-4",
        trajectories=[],
    )

    assert len(run.trajectories) == 0


def test_run_serialization():
    """Test Run serialization to dict."""
    run = Run(
        run_id="test-run-1",
        task="test-task",
        model="claude-sonnet-4",
        trajectories=[
            Trajectory(
                run_id="test-run-1",
                sample="1",
                messages=[
                    UserMessage(position=0, content="Test message"),
                ],
                scores={"main": ScalarScore(value=1.0)},
                metadata={},
            ),
        ],
    )

    run_dict = run.model_dump()

    assert run_dict["run_id"] == "test-run-1"
    assert run_dict["task"] == "test-task"
    assert run_dict["model"] == "claude-sonnet-4"
    assert len(run_dict["trajectories"]) == 1
    assert run_dict["trajectories"][0]["run_id"] == "test-run-1"
    assert run_dict["trajectories"][0]["sample"] == "1"


def test_trajectory_without_task_and_model():
    """Test that client Trajectory doesn't have task and model fields."""
    trajectory = Trajectory(
        run_id="test-run-1",
        sample="1",
        messages=[
            UserMessage(position=0, content="Test message"),
        ],
        scores={"main": ScalarScore(value=1.0)},
        metadata={},
    )

    # Verify task and model are not in the model
    assert not hasattr(trajectory, "task")
    assert not hasattr(trajectory, "model")

    # Verify serialization doesn't include task/model
    traj_dict = trajectory.model_dump()
    assert "task" not in traj_dict
    assert "model" not in traj_dict
    assert traj_dict["run_id"] == "test-run-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
