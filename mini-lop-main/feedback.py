"""
feedback.py - Coverage and Crash Feedback Module for Mini-Lop Fuzzer

This module handles three core functionalities:
1. Shared Memory Management: Setup and clearing of shared memory for coverage tracking
2. Crash Detection: Analysis of program exit codes to identify and classify crashes
3. Coverage Tracking: Management of edge coverage information

The shared memory is used to track edge coverage during program execution,
following AFL's design where the target program writes to a shared memory region
to indicate which edges were executed.
"""

import ctypes
import sys
import sysv_ipc

# Environment variable used by instrumented binaries to locate shared memory
SHM_ENV_VAR = "__AFL_SHM_ID"

# Coverage map size (2^16 = 65536 edges)
MAP_SIZE_POW2 = 16
MAP_SIZE = (1 << MAP_SIZE_POW2)

def setup_shm(libc):
    """
    Sets up shared memory for coverage feedback collection.
    
    This function:
    1. Creates a shared memory segment
    2. Maps it into the current process's address space
    3. Returns identifiers needed for target program communication
    
    Args:
        libc: C library instance for system calls
        
    Returns:
        tuple: (shmid, shmptr)
            shmid (int): Shared memory segment identifier
            shmptr (int): Pointer to mapped shared memory
            
    Raises:
        SystemExit: If shared memory creation or attachment fails
        
    Notes:
        The shared memory segment is created with 0600 permissions (user read/write only)
    """
    # Configure C function interfaces
    shmget = libc.shmget
    shmat = libc.shmat

    # Set correct types for shmat
    shmat.restype = ctypes.c_void_p
    shmat.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_int)

    # Create shared memory segment
    shmid = shmget(sysv_ipc.IPC_PRIVATE, MAP_SIZE, 
                   sysv_ipc.IPC_CREAT | sysv_ipc.IPC_EXCL | 0o600)

    if shmid < 0:
        sys.exit("cannot get shared memory segment with key %d" % (sysv_ipc.IPC_PRIVATE))

    # Map shared memory into process space
    shmptr = shmat(shmid, None, 0)
    if shmptr == 0 or shmptr == -1:
        sys.exit("cannot attach shared memory segment with id %d" % (shmid))

    print(f'created shared memory, shmid: {shmid}')
    return shmid, shmptr

def clear_shm(trace_bits):
    """
    Clears the coverage map in shared memory.
    
    Must be called before each execution to ensure accurate coverage tracking.
    
    Args:
        trace_bits: Pointer to shared memory region to clear
    """
    ctypes.memset(trace_bits, 0, MAP_SIZE)

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


