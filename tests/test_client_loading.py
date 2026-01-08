import pytest
from unittest.mock import AsyncMock, MagicMock
from lunette.client import LunetteClient
from lunette.models.trajectory import Trajectory
from lunette.models.messages import Message
from lunette.models.run import Run


@pytest.mark.asyncio
async def test_get_trajectory():
    # Mock response data
    mock_trajectory_data = {
        "sample": "sample_1",
        "messages": [
            {"role": "user", "content": "hello", "position": 0},
            {"role": "assistant", "content": "hi", "position": 1},
        ],
        "score": 1.0,
        "metadata": {},
        "solver_spec": {"model": "gpt-4", "tools": []},
    }

    # Setup mock client
    client = LunetteClient(base_url="http://test", api_key="test")
    client._client.get = AsyncMock(
        return_value=MagicMock(
            status_code=200,
            json=lambda: mock_trajectory_data,
            raise_for_status=lambda: None,
        )
    )

    # Test get_trajectory
    trajectory = await client.get_trajectory("traj_123")

    assert isinstance(trajectory, Trajectory)
    assert trajectory.sample == "sample_1"
    assert len(trajectory.messages) == 2
    client._client.get.assert_called_with("/trajectories/traj_123")


@pytest.mark.asyncio
async def test_get_run():
    # Mock response data
    mock_run_data = {
        "id": "run_123",
        "task": "test_task",
        "model": "gpt-4",
        "trajectories": [
            {
                "sample": "sample_1",
                "messages": [],
                "score": 1.0,
                "metadata": {},
                "solver_spec": {"model": "gpt-4", "tools": []},
            }
        ],
    }

    # Setup mock client
    client = LunetteClient(base_url="http://test", api_key="test")
    client._client.get = AsyncMock(
        return_value=MagicMock(status_code=200, json=lambda: mock_run_data, raise_for_status=lambda: None)
    )

    # Test get_run
    run = await client.get_run("run_123")

    assert isinstance(run, Run)
    assert run.id == "run_123"
    assert len(run.trajectories) == 1
    client._client.get.assert_called_with("/runs/run_123")
