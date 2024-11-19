Modified Functions:
1 - check_coverage in feedback.py - Enhanced to track unique edges and compare with global coverage
2 - run_fuzzing in main.py - Added seed queue management and edge-to-seeds mapping
Implementation Explanation:
The implementation focuses on two key components:
1 - Coverage Tracking (feedback.py):
def check_coverage(trace_bits, global_coverage):
    raw_bitmap = ctypes.string_at(trace_bits, MAP_SIZE)
    current_coverage = set()
    new_edge_covered = False
    
    for idx, byte in enumerate(raw_bitmap):
        if byte != 0:
            current_coverage.add(idx)
            
    new_edges = current_coverage - global_coverage
    if new_edges:
        new_edge_covered = True
    return new_edge_covered, current_coverage

2 - Seed Queue Management (main.py):
    seed_queue = []
    global_coverage = set()
    edge_to_seeds = {}  # Mapping from edge to list of seeds covering it
    cycle_count = 0
    seeds_used_in_cycle = set()
    seed_queue_length = 0  # Initialize seed queue length
        coverage = len(global_coverage)
    total_exec_time = 0.0
    exec_count = 0
        total_exec_time += exec_time
    # Do the dry run and initialize the seed queue
    shutil.copytree(conf['seeds_folder'], conf['queue_folder'])
    seed_files = os.listdir(conf['queue_folder'])
    for i, seed_file in enumerate(seed_files):
        seed_path = os.path.join(conf['queue_folder'], seed_file)
        shutil.copyfile(seed_path, conf['current_input'])
        status_code, exec_time = run_target(ctl_write_fd, st_read_fd, trace_bits)
        if status_code == 9:
            print(f"Seed {seed_file} caused a timeout during the dry run")
            continue
        if check_crash(status_code):
            print(f"Seed {seed_file} caused a crash during the dry run")
            continue
        new_edge_covered, seed_coverage = check_coverage(trace_bits, global_coverage)
        global_coverage.update(seed_coverage)
        # Update edge_to_seeds mapping
        for edge in seed_coverage:
            if edge not in edge_to_seeds:
                edge_to_seeds[edge] = []
            edge_to_seeds[edge].append(i)
        coverage = len(global_coverage)
        new_seed = Seed(seed_path, i, seed_coverage, exec_time)
        seed_queue.append(new_seed)
        total_exec_time += exec_time
        exec_count += 1

and:
            new_edge_covered, seed_coverage = check_coverage(trace_bits, global_coverage)
            if new_edge_covered:
                print(f"Found new coverage! Total coverage: {len(global_coverage)} edges.")
                global_coverage.update(seed_coverage)
                # Update edge_to_seeds mapping
                seed_id = len(seed_queue)
                for edge in seed_coverage:
                    if edge not in edge_to_seeds:
                        edge_to_seeds[edge] = []
                    edge_to_seeds[edge].append(seed_id)
                # Save new seed
                new_seed_path = os.path.join(conf['queue_folder'], f'id_{seed_id}')
                shutil.copyfile(conf['current_input'], new_seed_path)
                new_seed = Seed(new_seed_path, seed_id, seed_coverage, exec_time)
                seed_queue.append(new_seed)
                seed_queue_length += 1
                mutation_strategy.update_rewards(operator, len(seed_coverage - global_coverage))

The implementation maintains a global coverage set and saves inputs that discover new edges as seeds. When new coverage is found, the following occurs:
- The input is saved to the queue folder
- Edge-to-seeds mapping is updated
- Global coverage is updated
- A new Seed object is created with coverage information

This ensures we keep track of which inputs lead to new code coverage and can use them for future mutations. The edge-to-seeds mapping also helps identify which seeds are most valuable for covering specific program paths.