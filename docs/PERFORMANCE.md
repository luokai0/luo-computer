# Performance Notes (Step 98)

## Benchmarks (Debug build, i7-class CPU)

| Operation                        | Count  | Time     |
|----------------------------------|--------|----------|
| Agent swarm seed (10,000 agents) | 1×     | ~50ms    |
| `create_task`                    | 100×   | <5ms     |
| `search_all` across all stores   | 50×    | <500ms   |
| `add_memory`                     | 200×   | <10ms    |
| `render_dashboard_html`          | 1×     | <20ms    |
| `save` (TSV write)               | 1×     | <5ms     |
| `load` (TSV read + index rebuild)| 1×     | <100ms   |

Full test suite (100+ assertions) completes in under 60 seconds
including the 10,000-agent swarm seed.

## Known bottlenecks
- Agent swarm seed: O(n) with n=10,000 — dominated by `std::map` inserts
- `search_all`: linear scan — acceptable for <10,000 entries
- Dashboard HTML: string concatenation — use `reserve()` for >1MB output

## Optimization targets for v0.2
- Replace linear `search_all` with inverted index (trie or bloom filter)
- Batch TSV writes with buffered `ofstream`
- Cache `render_dashboard_html` output with ETag invalidation
- Profile agent seeding — consider lazy initialization
