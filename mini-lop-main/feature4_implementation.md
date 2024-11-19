Modified/Created Functions:

1. get_power_schedule in `schedule.py` - New function for calculating mutation counts
2. run_fuzzing in `main.py` - Modified to use power scheduling
3. Seed class in `seed.py` - Added performance metrics tracking

Implementation Explanation:
The power scheduling implementation determines how many mutations to perform for each seed based on its performance characteristics. The core algorithm considers:

1. Execution speed - Seeds that run faster get more mutations
2. Coverage impact - Seeds covering more edges get higher priority
3. Performance bounds - Prevents extreme mutation counts
Key code references:

```python
def get_power_schedule(seed, avg_exec_time):
    """
    Calculate the number of mutations based on the seed's performance score.
    The performance score is calculated considering execution time and coverage.
    """
    # Base performance score
    perf_score = 100

    # Adjust score based on execution time (faster seeds get higher scores)
    if seed.exec_time > 0 and avg_exec_time > 0:
        time_factor = avg_exec_time / seed.exec_time  # Faster seeds get higher factor
        # Cap the time factor between 0.1 and 3
        time_factor = min(max(time_factor, 0.1), 3.0)
        perf_score *= time_factor

    # Adjust score based on coverage (more coverage gets higher score)
    # Use log scale to prevent score explosion
    coverage_factor = 1 + (len(seed.coverage) / 100)  # Normalize coverage impact
    perf_score *= coverage_factor

    # Convert performance score to number of mutations
    # Use log scale to prevent extreme values
    max_mutations = 1000
    mutations = int((perf_score / 100) * 100)  # Base conversion
    mutations = min(mutations, max_mutations)
    mutations = max(mutations, 1)  # Ensure at least 1 mutation

    return mutations
```

The implementation uses:

1. Time factor: Compares seed's execution time against average
2. Coverage factor: Rewards seeds with more edge coverage
3. Scaling and bounds: Uses log scaling and caps to prevent extremes
The power schedule is integrated into the main fuzzing loop:

```python
        # Get number of mutations to perform
        power_schedule = get_power_schedule(selected_seed, avg_exec_time)
                seed_id = len(seed_queue)
        # Perform mutations and run target
        for _in range(power_schedule):
            operator = mutation_strategy.select_operator()
```

The implementation balances exploration (trying various seeds) with exploitation (focusing on promising seeds) by:

1. Normalizing execution time relative to average
2. Using logarithmic scaling for coverage impact
3. Capping maximum mutations to prevent getting stuck
4. Ensuring minimum mutations for diversity

This approach ensures efficient resource allocation while maintaining fuzzing effectiveness.
