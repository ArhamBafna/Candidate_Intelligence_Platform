---
name: python-performance-optimization
description: Use when Python code is slow, a performance regression is reported, or measured CPU, memory, database, or I/O bottlenecks need diagnosis and optimization.
---

# Python Performance Optimization

Optimize measured Python bottlenecks without changing behavior.

## Workflow

1. **Measure.** Reproduce the workload and record execution time, memory, CPU, or I/O metrics relevant to the complaint. Done when a baseline and workload are recorded.
2. **Profile.** Use cProfile for CPU, line profiling for a narrowed function, memory profiling or `tracemalloc` for allocations, and py-spy for a running process. Done when the dominant cost is identified in named code.
3. **Choose.** Prefer algorithmic and data-structure changes, then implementation, batching, caching, or concurrency where the profile supports them. Read `references/details.md` for standard patterns; read `references/advanced-patterns.md` only for NumPy, multiprocessing, async I/O, database, memory, or benchmarking branches. Done when one change has a measured rationale and known tradeoffs.
4. **Change.** Apply the smallest behavior-preserving change. Done when implementation and required tests are updated.
5. **Verify.** Repeat the same workload, compare against baseline, and run the repository's existing tests. Done when the target metric improves or the evidence shows optimization is not justified, with no relevant regression.

## Decision rules

- Profile before optimizing; optimize hot paths, not guesses.
- Prefer appropriate data structures and built-ins.
- Use generators for large streams and batch I/O/database work.
- Add caching only when inputs are stable and invalidation is defined.
- Use NumPy, multiprocessing, or async I/O only when workload and dependencies support them.
- Preserve correctness, resource cleanup, and observable API behavior.

## References

- Standard profiling and implementation patterns: `references/details.md`
- Advanced optimization patterns and tradeoffs: `references/advanced-patterns.md`
