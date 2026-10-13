# jobfinder

A small tool that watches the job boards of the companies you care about and keeps the postings that match your search.

It queries the **public APIs of applicant tracking systems (ATS)** such as Greenhouse, Lever and Ashby, for a list of companies you configure. It stores the raw responses, parses the postings into a common format, keeps only the ones in your target locations, and remembers which ones it has already seen so that only *new* postings need attention.

## How it works

```
config.yaml
    |
    v
for each company of each ATS:
    HTTP GET (retry + backoff + delay between requests)
    |-- parse postings into a common Job model
    |-- keep the jobs whose location matches the config
    '-- drop the jobs already seen in previous runs
    |
    v
new jobs  ->  (next step: LLM scoring and notification)
```

Design choices worth knowing:

- **One parser per ATS.** Each ATS has its own response format. Parsers turn them into the same `Job` model (id, title, location, url, dates in UTC, plain-text description).
- **No API key needed.** Only the public, read-only endpoints of each ATS are used.
- **Polite by design.** Requests are sequential, spaced by a configurable delay, with retries and exponential backoff on 429/5xx responses (the `Retry-After` header is honoured).
- **Pluggable storage.** The pipeline only depends on a `JobStore` interface. The JSON-files backend is the first implementation.

## Supported ATS

| ATS | Config key |
|---|---|
| Greenhouse | `greenhouse` |
| Lever | `lever` |
| Ashby | `ashbyhq` |

To find the **token** of a company, open its careers page: it is the identifier in the URL of the job board (for example `boards.greenhouse.io/<token>`).

## Installation

The project uses [uv](https://docs.astral.sh/uv/). The Python version is pinned in `.python-version`.

```bash
git clone <your-repository-url>
cd jobfinder
uv sync
```

## Configuration

Everything is configured in a YAML file (`config.yaml` by default). It is validated at startup: an unknown key, a missing field or an invalid value stops the program with an explicit error before any request is made.

```yaml
search:
  # A job is kept if its location contains at least one of these terms.
  locations: ["Paris", "Ile-de-France"]

http:
  timeout_s: 20          # timeout of each request, in seconds
  delay_s: 0.5           # pause between two companies, in seconds
  retry:
    number: 5
    backoff_factor: 1.0
    respect_retry_after_header: true
    status_forcelist: [429, 500, 502, 503, 504]

storage:
  storage_type: json     # the only backend available for now
  data_dir: data

ats:
  - name: greenhouse
    endpoint: "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    companies:
    - name: "Example"
      token: "example"
  - name: lever
    endpoint: "https://api.lever.co/v0/postings/{token}"
    companies:
    - name: "Example"
      token: "example"
  - name: ashbyhq
    endpoint: "https://api.ashbyhq.com/posting-api/job-board/{token}"
    companies:
    - name: "Example"
      token: "example"
```

### Sections

| Section | Purpose |
|---|---|
| `search.locations` | Terms matched against the location of each job. Matching is case-insensitive, accents are **not** ignored (`Ile-de-France` and `Île-de-France` are different terms). The list must contain at least one non-empty term. |
| `http` | Timeout, delay between companies, and retry policy of the HTTP session. |
| `storage` | Where results are kept. See [Data layout](#data-layout). |
| `ats` | One entry per ATS, with its endpoint (`{token}` is replaced by each company's token) and the list of companies to query. |

### Good to know

- Tokens are used to build file paths, so they must not contain `/`, `\` or `..`.
- Secrets (API keys, passwords) never go in this file: use environment variables.

## Running

```bash
uv run jobfinder
```

Each run fetches every configured company, saves the raw responses, and logs how many jobs matched and how many are new.

You can run for a specific ats with

```bash
uv run jobfinder --ats greenhouse
```

Or run it on a specific company if specifying a company token

```bash
uv run jobfinder --company docker
```

## Data layout

With the JSON storage backend, everything is written under `data_dir`:

```
data/
|-- ashbyhq/
|   '--company_a.json
|-- greenhouse/
|   '-- company_b.json      # raw API response of one company
|-- lever/
|   '-- company_c.json
'-- seen.json              # sorted list of the job uids already processed
```

- A job uid looks like `greenhouse:company_a:7811470003` (`ats:token:id`).
- Files are written atomically (temporary file, then rename), so an interrupted run never leaves a half-written file.
- Raw responses are replaced at each run. If a company fails, its previous file is kept.
- `data_dir` is git-ignored: it only contains run data.

## Development

### Project layout

```
src/jobfinder/
|-- main.py        # entry point: loads the config and assembles the components
|-- config.py      # typed, validated configuration
|-- models.py      # Job and Target models
|-- adapters.py    # one parser per ATS
|-- search.py      # fetching and filtering
|-- session.py     # building a http session as configured
'-- storage/       # JobStore interface and its implementations
tests/
|-- fixtures/      # samples of API responses, one folder per ATS
'-- ...
```

### Tests

```bash
uv run pytest
```

HTTP calls are never made in tests: the session is replaced by a fake that returns a JSON file from `tests/fixtures/`.

**Adding a test case for an ATS:**

1. Save an API response in `tests/fixtures/<ats>/<scenario>.json`. Keep two or three postings and strip what is not needed. Name the file after the scenario (`secondary_locations.json`, `empty_board.json`), not after a company or a date.
2. Add a line to the `parametrize` list of the matching parser test, with the expected `Job` objects.

Storage backends share the same behaviour contract: any new backend should pass the same tests as `JsonStore`.

### Lint and format

[Ruff](https://docs.astral.sh/ruff/) is used for both. They are two separate commands, and the **linter must run first**: it also sorts the imports, which the formatter does not do.

```bash
uv run ruff check . --fix   # lint, with safe automatic fixes
uv run ruff format .        # format
```

To check without modifying anything (useful in CI):

```bash
uv run ruff check .
uv run ruff format . --check
```

Before each commit, run both commands and then `uv run pytest`.

### Adding things

- **A new ATS:** write a parser in `adapters.py`, register it under the name used in the YAML, add fixtures and tests.
- **A new storage backend:** implement the `JobStore` interface, register it in the storage factory, and run the shared storage tests against it.

## Roadmap

- Score new jobs against a personal profile with an LLM.
- Add more tests
- Send a notification when a job matches.
- SQLite storage backend.