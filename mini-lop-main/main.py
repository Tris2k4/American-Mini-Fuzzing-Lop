"""
main.py - Main Module for Mini-Lop Fuzzer

This module implements the core fuzzing loop and coordinates all components:
1. Fork Server: Manages efficient program execution
2. Coverage Tracking: Monitors program behavior
3. Mutation Engine: Generates new test cases
4. Crash Detection: Identifies and saves program failures
"""

import argparse
import signal
from conf import *
from libc import *
from feedback import *
from execution import *
from seed import *
from schedule import *
from mutation import *

# Fork server file descriptor (must match target program)
FORKSRV_FD = 198

def signal_handler(sig, frame):
    print('You pressed Ctrl+C! Ending the fuzzing session...')
    os._exit(0)

def run_forkserver(conf, ctl_read_fd, st_write_fd):
    """
    Sets up and runs the fork server in the target process.
    
    Args:
        conf: Fuzzer configuration
        ctl_read_fd: Control read file descriptor
        st_write_fd: Status write file descriptor
    """
    os.dup2(ctl_read_fd, FORKSRV_FD)
    os.dup2(st_write_fd, FORKSRV_FD + 1)
    # prepare command
    cmd = [conf['target']] + conf['target_args']
    print(cmd)
    print(f'shmid is {os.environ[SHM_ENV_VAR]}')
    print(f'st_write_fd: {st_write_fd}')

    # eats stdout and stderr of the target
    dev_null_fd = os.open(os.devnull, os.O_RDWR)
    os.dup2(dev_null_fd, 1)
    os.dup2(dev_null_fd, 2)

    os.execv(conf['target'], cmd)

def run_fuzzing(conf, st_read_fd, ctl_write_fd, trace_bits):
    """
    Main fuzzing loop implementation.
    
    Args:
        conf: Fuzzer configuration
        st_read_fd: Status read file descriptor
        ctl_write_fd: Control write file descriptor
        trace_bits: Shared memory for coverage feedback
    """
    read_bytes = os.read(st_read_fd, 4)
    if len(read_bytes) == 4:
        print("Forkserver is up! Starting fuzzing... Press Ctrl+C to stop.")

    seed_queue = []
    global_coverage = set()
    edge_to_seeds = {}  # Mapping from edge to list of seeds covering it
    cycle_count = 0
    seeds_used_in_cycle = set()
    seed_queue_length = 0  # Initialize seed queue length

    total_exec_time = 0.0
    exec_count = 0

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
    # Calculate average execution time
    avg_exec_time = total_exec_time / exec_count if exec_count > 0 else 0.1

    # Update favored seeds after dry run
    update_favored_seeds(seed_queue, edge_to_seeds)

    print(f"Dry run finished. Initial coverage: {len(global_coverage)} edges.")

    # Initialize cycle tracking
    seeds_used_in_cycle = set()
    cycle_seed_count = len(seed_queue)
    cycle_count = 0
    
    mutation_strategy = MutationStrategy(conf)
    
    while True:
        # Select next seed using the new function
        selected_seed, seeds_used_in_cycle, cycle_seed_count, new_cycle = \
            select_next_seed(seed_queue, seeds_used_in_cycle, cycle_seed_count)
            
        if new_cycle:
            cycle_count += 1
            print(f"Starting new cycle {cycle_count}")
            # Update favored seeds at the beginning of each cycle
            update_favored_seeds(seed_queue, edge_to_seeds)
            
        if not selected_seed:
            print("No seeds available!")
            break
            
        # Get number of mutations to perform
        power_schedule = get_power_schedule(selected_seed, avg_exec_time)
        
        # Perform mutations and run target
        for _ in range(power_schedule):
            operator = mutation_strategy.select_operator()
            if operator == 'havoc':
                mutation_strategy.havoc_mutator.mutate(selected_seed)
            else:
                mutation_strategy.splice_mutator.mutate(selected_seed, seed_queue)
            
            status_code, exec_time = run_target(ctl_write_fd, st_read_fd, trace_bits)
            total_exec_time += exec_time
            exec_count += 1
            avg_exec_time = total_exec_time / exec_count
            
            if status_code == 9:
                print("Timeout, skipping this input")
                continue
                
            if check_crash(status_code):
                crash_path = save_crash_input(conf, selected_seed.path, status_code)
                print(f"Crash saved to {crash_path}")
                # Update mutation strategy with crash information
                mutation_strategy.update_rewards(operator, 0, crashed=True)
                continue
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

def save_crash_input(conf, seed_path=None, status_code=None):
    """
    Save crash-triggering input to crashes folder.
    
    Args:
        conf: Fuzzer configuration
        seed_path: Path to seed that led to crash
        status_code: Exit status of crashed program
    """
    timestamp = int(time.time())
    if seed_path:
        orig_filename = os.path.basename(seed_path)
        crash_filename = f"crash_{timestamp}_{orig_filename}"
    else:
        crash_filename = f"crash_{timestamp}"
    
    crash_path = os.path.join(conf['crashes_folder'], crash_filename)
    shutil.copyfile(conf['current_input'], crash_path)
    return crash_path

def update_favored_seeds(seed_queue, edge_to_seeds):
    """
    Update which seeds are marked as favored based on coverage.
    
    Args:
        seed_queue: List of all seeds
        edge_to_seeds: Mapping of edges to seeds covering them
    """
    # Reset favored status
    for seed in seed_queue:
        seed.unmark_favored()
    # For each edge, find the seed with minimal (exec_time * file_size)
    for edge, seed_ids in edge_to_seeds.items():
        # Get the seeds covering this edge
        seeds = [seed_queue[seed_id] for seed_id in seed_ids]
        # Sort seeds by (exec_time * file_size)
        seeds.sort(key=lambda s: s.get_valuation())
        # Mark the first seed as favored
        seeds[0].mark_favored()

def main():
    """Entry point for Mini-Lop fuzzer"""
    print("====== Welcome to use Mini-Lop ======")

    parser = argparse.ArgumentParser(description='Mini-Lop: A lightweight grey-box fuzzer')
    parser.add_argument('--config', '-c', required=True, help='Path to config file', type=str)
    args = parser.parse_args()

    config_path = os.path.abspath(args.config)
    config_valid, conf = parse_config(config_path)

    if not config_valid:
        print("Config file is not valid")
        return

    libc = get_libc()

    shmid, trace_bits = setup_shm(libc)
    # share the shmid with the target via an environment variable
    os.environ[SHM_ENV_VAR] = str(shmid)
    # clean the shared memory
    clear_shm(trace_bits)

    signal.signal(signal.SIGINT, signal_handler)

    # setup pipes for communication
    # st: status, ctl: control
    (st_read_fd, st_write_fd) = os.pipe()
    (ctl_read_fd, ctl_write_fd) = os.pipe()

    child_pid = os.fork()

    if child_pid == 0:
        run_forkserver(conf, ctl_read_fd, st_write_fd)
    else:
        run_fuzzing(conf, st_read_fd, ctl_write_fd, trace_bits)

if __name__ == '__main__':
    main()
