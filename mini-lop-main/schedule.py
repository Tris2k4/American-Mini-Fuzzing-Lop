import random
import os


def select_next_seed(seed_queue, seeds_used_in_cycle=None, cycle_seed_count=None):
    """
    Select the next seed using AFL's favored seed prioritization strategy.
    
    Args:
        seed_queue: List of available seeds
        seeds_used_in_cycle: Set of seed IDs used in current cycle
        cycle_seed_count: Number of seeds at start of cycle
        
    Returns:
        tuple: (selected_seed, seeds_used_in_cycle, cycle_seed_count, new_cycle)
    """
    if not seed_queue:
        return None, seeds_used_in_cycle, cycle_seed_count, False
        
    # Initialize cycle tracking if needed
    if seeds_used_in_cycle is None:
        seeds_used_in_cycle = set()
    if cycle_seed_count is None:
        cycle_seed_count = len(seed_queue)
        
    # Check if we need to start a new cycle
    new_cycle = False
    if len(seeds_used_in_cycle) >= cycle_seed_count:
        seeds_used_in_cycle.clear()
        cycle_seed_count = len(seed_queue)
        new_cycle = True
        
    # Find unused seeds in current cycle
    unused_seeds = [s for s in seed_queue if s.seed_id not in seeds_used_in_cycle]
    
    # Find unused favored seeds
    unused_favored = [s for s in unused_seeds if s.favored]
    
    # Select next seed
    if unused_favored and random.random() < 0.9:  # 90% chance to use favored seed
        selected_seed = random.choice(unused_favored)
    else:
        selected_seed = random.choice(unused_seeds)
        
    seeds_used_in_cycle.add(selected_seed.seed_id)
    
    return selected_seed, seeds_used_in_cycle, cycle_seed_count, new_cycle


# get the power schedule (# of new test inputs to generate for a seed)
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

