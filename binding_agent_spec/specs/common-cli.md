# Common CLI Contract

All wrappers follow the same high-level pattern.

## Common invocation styles

### 1. Structured request
```bash
tool subcommand --request request.yaml --json-out result.json
```

### 2. Direct flags
```bash
tool subcommand [tool-specific flags] --json-out result.json
```

### 3. STDIN JSON
```bash
cat request.json | tool subcommand --stdin-json --json-out result.json
```

## Common flags

- `--request <path>`: YAML or JSON request document
- `--stdin-json`: read request JSON from stdin
- `--json-out <path>`: normalized result envelope
- `--yaml-out <path>`: optional YAML mirror of normalized result
- `--artifacts-dir <dir>`: native upstream artifacts
- `--run-id <string>`: caller-supplied run identifier
- `--workspace <dir>`: working directory
- `--overwrite`: overwrite existing outputs
- `--timeout-s <int>`: hard timeout in seconds
- `--threads <int>`: CPU worker count
- `--device <string>`: device selector, for example `cuda:0` or `cpu`
- `--verbose`: verbose logs
- `--quiet`: minimal logs
- `--dry-run`: validate request and print resolved execution plan without running
- `--emit-command`: print the upstream command that would be executed
- `--emit-request-resolved <path>`: write the fully resolved request after defaulting and path expansion
- `--version`
- `doctor`: environment diagnostics
- `schema`: print or write the supported request/result schema names

## Exit codes

- `0`: success
- `2`: validation error
- `3`: input missing or unreadable
- `4`: upstream tool execution failure
- `5`: timeout
- `6`: partial success with warnings
- `7`: unsupported request combination

## Normalized result envelope

Every wrapper writes a JSON object with:

- `apiVersion`
- `kind`
- `metadata`
- `tool`
- `toolVersion`
- `wrapperVersion`
- `status`
- `inputsResolved`
- `parametersResolved`
- `summary`
- `artifacts`
- `warnings`
- `errors`
- `provenance`
- `runtimeSeconds`

Upstream stdout and stderr may be preserved as artifacts but are not the primary machine interface.
