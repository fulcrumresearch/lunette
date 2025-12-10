# Running Agents on Lunette

You can run your agent evals on lunette's infrastructure. We provide a sandbox API where you can define and run agents in isolated sandboxes on the cloud.

This allows our investigators to then inspect and analyze your agent's work after the fact, directly in the environment from which it ran.

We recommend this for a few reasons:
- it makes investigations more powerful and accurate.
- it's efficient - we cache agent images, and this makes it easy to scale how many sandboxes you use at once.

## Inspect AI

Add `--sandbox lunette` to your eval command:

```bash
inspect eval your_task.py --sandbox lunette
```

Lunette registers as an Inspect sandbox provider. Your task runs in a cloud container that's preserved for later investigation.

This also works for most [off-the-shelf inspect evals](https://inspect.ai-safety-institute.org.uk/evals/). For evals that hardcode Docker, you can register the Lunette sandbox—it takes the same inputs but runs on the cloud.

See the [example Inspect task](https://github.com/fulcrumresearch/lunette/blob/main/examples/environment/inspect_task.py) for a complete example.

## SDK

You can use `LunetteClient` to create sandboxes programmatically.

### Sandbox API

**Create a sandbox**:

```python
async with LunetteClient() as client:
    sandbox = await client.create_sandbox({"image": "python:3.11-slim"})
```

**Execute commands**:

```python
result = await sandbox.aexec("python3 -c 'print(2**100)'")
print(result.stdout)      # output
print(result.stderr)      # errors
print(result.success)     # True if exit code 0
print(result.exit_code)   # exit code
```

**Upload/download files**:

```python
await sandbox.aupload("/path/to/local/file", "/path/in/sandbox")
await sandbox.adownload("/path/in/sandbox", "/path/to/local/file")
```

**Clean up**:

```python
await sandbox.destroy()
```

### Configuration

You can specify different Docker images when creating sandboxes:

```python
# Python environment
sandbox = await client.create_sandbox({"image": "python:3.11-slim"})

# Node.js environment
sandbox = await client.create_sandbox({"image": "node:20-slim"})

# Custom image
sandbox = await client.create_sandbox({"image": "my-registry/my-image:latest"})
```

See the [full SDK example](https://github.com/fulcrumresearch/lunette/blob/main/examples/environment/custom_task.py) for a complete script using the tracing and sandbox SDK.
