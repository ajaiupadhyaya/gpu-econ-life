# gpu-econ-life

Market-implied economic life of AI accelerators, estimated from GPU rental prices and compared
to hyperscaler book depreciation. See [docs/proposal.md](docs/proposal.md) for the full proposal
and [CLAUDE.md](CLAUDE.md) for the project rules.

Status: Phase 1 collector built and run once; deployment to a host is pending. The plan was
revised after Phase 0, and [docs/proposal_review.md](docs/proposal_review.md) explains why.

```bash
uv sync
make test
make coverage-preview   # Wayback index counts only; downloads no page contents
make collect            # one live collection run across all sources
make health             # compare today's rows with the previous seven days
```
