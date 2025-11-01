"""Test script for investigation API."""

import httpx
import yaml

# Example plan
plan_yaml = """
name: test_investigation
type: investigation
trajectory_filters:
  filters:
    score: [lt, 0.5]
agents:
  - name: test_analyzer
    prompt: |
      You are testing the investigation system.
      Just output: {"bottleneck_description": "Test bottleneck", "issues": []}
"""

# Make request
response = httpx.post(
    "http://localhost:8000/api/investigations/run",
    json={
        "plan": plan_yaml,
        "sandbox_id": "a6250c1de61a",
    }
)

print("Status:", response.status_code)
print("Response:", response.json())
