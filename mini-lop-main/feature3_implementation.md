Modified/Created Functions:
1 - `update_favored_seeds` in `main.py` - New function to mark favored seeds
2 - `select_next_seed` in `schedule.py` - New function for seed selection with prioritization
3 - `Seed` class in `seed.py` - Added favored status tracking

Implementation Explanation:
The implementation follows AFL's seed prioritization strategy with three key components:
1 - Seed Status Tracking (`seed.py`):
class Seed:
    def __init__(self, path, seed_id, coverage, exec_time):
        self.favored = False  # Track favored status
        
    def mark_favored(self):
        self.favored = True
        
    def unmark_favored(self):
        self.favored = False
2 - Seed Prioritization (`schedule.py`):
def select_next_seed(seed_queue, seeds_used_in_cycle, cycle_seed_count):
    # Find unused seeds in current cycle
    unused_seeds = [s for s in seed_queue if s.seed_id not in seeds_used_in_cycle]
    
    # Find unused favored seeds
    unused_favored = [s for s in unused_seeds if s.favored]
    
    # 90% chance to use favored seed if available
    if unused_favored and random.random() < 0.9:
        selected_seed = random.choice(unused_favored)
    else:
        selected_seed = random.choice(unused_seeds)
    
    return selected_seed, seeds_used_in_cycle, cycle_seed_count, new_cycle
3 - Favored Seed Management (`main.py`):
def update_favored_seeds(seed_queue, edge_to_seeds):
    # Reset favored status
    for seed in seed_queue:
        seed.unmark_favored()
    # For each edge, find seed with best performance
    for edge, seed_ids in edge_to_seeds.items():
        seeds = [seed_queue[seed_id] for seed_id in seed_ids]
        seeds.sort(key=lambda s: s.get_valuation())
        seeds[0].mark_favored()

The implementation prioritizes seeds that provide unique coverage with good performance (small file size and fast execution). For each edge, we mark as "favored" the seed that covers it with the best performance score. During seed selection, we have a 90% chance of choosing from favored seeds when available, ensuring efficient exploration of the program's state space.