Modified Functions:
1 - `check_crash` in `feedback.py` - Enhanced crash detection with signal classification
2 - `save_crash_input` in `main.py` - New function to save crash-inducing inputs
3 - `run_fuzzing` in `main.py` - Added crash verification and storage logic

Implementation Explanation:

The implementation focuses on three key components:

1 - Enhanced Crash Detection (`feedback.py`):
def check_crash(status_code):
    """
    Analyzes program exit status to detect and classify crashes.
    
    This function identifies crashes by:
    1. Checking for known crash signals
    2. Detecting core dumps
    3. Extracting the actual signal from the status code
    
    Args:
        status_code (int): Program exit status to analyze
        
    Returns:
        bool: True if the status indicates a crash, False otherwise
        
    Notes:
        - Status codes encode both signal and core dump information:
          * High bit (0x80): Indicates core dump if set
          * Low 7 bits: Contains the actual signal number
        - Example: status 139 (0x8B) means:
          * 0x80 set -> core dump generated
          * 0x0B (11) -> SIGSEGV signal
    """
    # Dictionary of recognized crash signals
    crash_signals = {
        1: "SIGHUP",    # Hangup (terminal disconnected)
        2: "SIGINT",    # Interrupt (Ctrl+C)
        3: "SIGQUIT",   # Quit (Ctrl+\)
        4: "SIGILL",    # Illegal instruction
        6: "SIGABRT",   # Abort (assert failure)
        7: "SIGBUS",    # Bus error (bad memory access)
        8: "SIGFPE",    # Floating point exception
        9: "SIGKILL",   # Kill (immediate termination)
        11: "SIGSEGV",  # Segmentation fault
        13: "SIGPIPE",  # Broken pipe
        14: "SIGALRM",  # Alarm clock
        15: "SIGTERM",  # Termination request
        24: "SIGXCPU",  # CPU time limit exceeded
        25: "SIGXFSZ",  # File size limit exceeded
        31: "SIGSYS"    # Bad system call
    }
    # Extract core dump flag and actual signal
    is_core_dump = (status_code & 0x80) != 0  # Check high bit
    actual_signal = status_code & 0x7f         # Get low 7 bits
    
    # Determine if status indicates a crash
    if actual_signal in crash_signals or is_core_dump:
        signal_name = crash_signals.get(actual_signal, "Unknown signal")
        print(f"Found a crash! Signal: {signal_name} ({actual_signal})")
        if is_core_dump:
            print("Core dump detected!")
        return True
    return False

2 - Save Crash-Inducing Inputs (`main.py`):
def save_crash_input(conf, seed_path=None, status_code=None):
    """
    Save crash-triggering input to crashes folder.
    shmid, trace_bits = setup_shm(libc)
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
    parser = argparse.ArgumentParser(description='Mini-Lop: A lightweight grey-box fuzzer')
    crash_path = os.path.join(conf['crashes_folder'], crash_filename)
    shutil.copyfile(conf['current_input'], crash_path)
    return crash_path

3 - Crash Storage (`main.py`):
            if check_crash(status_code):
                crash_path = save_crash_input(conf, selected_seed.path, status_code)
                print(f"Crash saved to {crash_path}")
                # Update mutation strategy with crash information
                mutation_strategy.update_rewards(operator, 0, crashed=True)
                continue

The implementation provides robust crash handling by:
- Detecting crashes through signal analysis and core dump detection
- Saving crash-inducing inputs with original seed information
The crash detection system identifies various crash types (SIGSEGV, SIGABRT, etc.) and saves the inputs that triggered them, allowing for later reproduction and analysis.