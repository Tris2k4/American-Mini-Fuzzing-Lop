"""
mutation.py - Mutation Strategies Module for Mini-Lop Fuzzer

This module implements various mutation strategies for test case generation:
1. Havoc Mutator: Implements aggressive random mutations
2. Splice Mutator: Combines parts of different test cases
3. Mutation Strategy: Manages and selects between different mutation operators

The mutation operators are designed to generate new test inputs that might trigger
different program behaviors, crashes, or increase code coverage.
"""

import random
import struct
import os

INTERESTING_16 = [
    0, -32768, 32767, -1, 1,  # Min/max values for 16-bit integers
    -128, 128, 255, -256, 256,  # Common boundary values
    65535  # Maximum unsigned 16-bit value
]

INTERESTING_32 = [
    0, -2147483648, 2147483647, -1, 1,  # Min/max values for 32-bit integers
    -32768, 32767, -65536, 65535,  # Common boundary values
    -100663046, 100663046  # Large values
]

INTERESTING_64 = [
    0, -1, 1,  # Common edge cases
    -4294967296, 4294967296,  # 32-bit boundaries
    -2147483648, 2147483647,  # 32-bit integer limits
    9223372036854775807, -9223372036854775808  # 64-bit integer limits
]

class HavocMutator:
    """
    Implements aggressive random mutations on test cases.
    
    This mutator applies various mutation strategies including:
    - Bit flips
    - Integer mutations
    - Interesting value insertions
    - Chunk replacements
    - Dictionary-based mutations
    - Arithmetic operations
    """
    
    def __init__(self, conf):
        """
        Initialize the havoc mutator.
        
        Args:
            conf (dict): Configuration dictionary containing:
                - dictionary_file: Path to mutation dictionary
                - current_input: Path to write mutated inputs
        """
        self.conf = conf
        self.dictionary = self.load_dictionary(conf.get('dictionary_file'))
        
    def load_dictionary(self, dict_file):
        """
        Load mutation dictionary from file.
        
        Args:
            dict_file (str): Path to dictionary file
            
        Returns:
            list: List of byte sequences to use in mutations
            
        Notes:
            Dictionary format:
            - Lines starting with '#' are ignored
            - Tokens are enclosed in quotes
            - Empty lines are skipped
        """
        if not dict_file or not os.path.exists(dict_file):
            return []
        
        tokens = []
        with open(dict_file, 'rb') as f:
            for line in f:
                if line.startswith(b'#') or not line.strip():
                    continue
                if b'"' in line:
                    token = line.split(b'"')[1]
                    tokens.append(token)
        return tokens

    def mutate(self, seed):
        """
        Main mutation function that randomly applies various mutation strategies.
        
        Args:
            seed: Seed object containing the test case to mutate
            
        Notes:
            - Number of mutations scales with input size
            - Mutations are applied randomly
            - Result is written to conf['current_input']
        """
        with open(seed.path, 'rb') as f:
            data = bytearray(f.read())
            
        if len(data) < 8:
            return
            
        num_mutations = random.randint(1, max(4, len(data) // 100))
        
        for _ in range(num_mutations):
            mutation_choice = random.randint(0, 6)
            
            if mutation_choice == 0:
                self.bit_flip_mutation(data)
            elif mutation_choice == 1:
                self.integer_mutation(data)
            elif mutation_choice == 2:
                self.interesting_value_mutation(data)
            elif mutation_choice == 3:
                self.chunk_replacement_mutation(data)
            elif mutation_choice == 4:
                self.dictionary_insert_mutation(data)
            elif mutation_choice == 5:
                self.dictionary_replace_mutation(data)
            else:
                self.arithmetic_mutation(data)
                
        with open(self.conf['current_input'], 'wb') as f:
            f.write(data)

    def bit_flip_mutation(self, data):
        """Flip random bits in the data"""
        idx = random.randint(0, len(data) - 1)
        bit_pos = random.randint(0, 7)
        data[idx] ^= (1 << bit_pos)

    def integer_mutation(self, data):
        """Mutate 2/4/8 byte integers with random values"""
        sizes = [(2, '<h', -32768, 32767),
                (4, '<i', -2147483648, 2147483647),
                (8, '<q', -9223372036854775808, 9223372036854775807)]
        
        size, fmt, min_val, max_val = random.choice(sizes)
        if len(data) < size:
            return
            
        idx = random.randint(0, len(data) - size)
        value = random.randint(min_val, max_val)
        struct.pack_into(fmt, data, idx, value)

    def interesting_value_mutation(self, data):
        """Replace integers with interesting values"""
        sizes = [
            (2, '<h', [-32768, 32767, -1, 0, 1, -128, 127, 255, -256, 256, 65535 & 0x7fff]),
            (4, '<i', INTERESTING_32),
            (8, '<q', INTERESTING_64)
        ]
        
        size, fmt, interesting_vals = random.choice(sizes)
        if len(data) < size:
            return
            
        idx = random.randint(0, len(data) - size)
        value = random.choice(interesting_vals)
        
        try:
            struct.pack_into(fmt, data, idx, value)
        except struct.error:
            # If value is too large for the format, use a bounded value
            if value > 0:
                struct.pack_into(fmt, data, idx, (1 << (size * 8 - 1)) - 1)  # Max positive
            else:
                struct.pack_into(fmt, data, idx, -(1 << (size * 8 - 1)))     # Max negative

    def chunk_replacement_mutation(self, data):
        """Replace a chunk of bytes with another chunk from the same file"""
        if len(data) < 4:
            return
            
        chunk_size = random.randint(2, min(32, len(data) // 2))
        src_pos = random.randint(0, len(data) - chunk_size)
        dst_pos = random.randint(0, len(data) - chunk_size)
        
        chunk = data[src_pos:src_pos + chunk_size]
        data[dst_pos:dst_pos + chunk_size] = chunk

    def arithmetic_mutation(self, data):
        """Perform arithmetic operations on integers"""
        sizes = [(2, '<h', -256, 256),
                (4, '<i', -65536, 65536),
                (8, '<q', -4294967296, 4294967296)]
        
        size, fmt, min_delta, max_delta = random.choice(sizes)
        if len(data) < size:
            return
            
        idx = random.randint(0, len(data) - size)
        value = struct.unpack_from(fmt, data, idx)[0]
        delta = random.randint(min_delta, max_delta)
        
        try:
            struct.pack_into(fmt, data, idx, value + delta)
        except struct.error:
            # If overflow occurs, wrap around
            if delta > 0:
                struct.pack_into(fmt, data, idx, min_delta)
            else:
                struct.pack_into(fmt, data, idx, max_delta)

    def dictionary_insert_mutation(self, data):
        """Insert dictionary token at random position"""
        if not self.dictionary:
            return
            
        token = random.choice(self.dictionary)
        if len(data) < 2:
            data.extend(token)
        else:
            pos = random.randint(0, len(data) - 1)
            data[pos:pos] = token

    def dictionary_replace_mutation(self, data):
        """Replace bytes with dictionary token"""
        if not self.dictionary or len(data) < 2:
            return
            
        token = random.choice(self.dictionary)
        if len(token) > len(data):
            return
            
        pos = random.randint(0, len(data) - len(token))
        data[pos:pos + len(token)] = token

class SpliceMutator:
    """
    Implements test case splicing followed by havoc mutations.
    
    This mutator:
    1. Selects two different test cases
    2. Splices them at random points
    3. Applies havoc mutations to the result
    """
    
    def __init__(self, conf):
        """
        Initialize splice mutator.
        
        Args:
            conf (dict): Configuration dictionary
        """
        self.conf = conf
        self.havoc_mutator = HavocMutator(conf)
        
    def mutate(self, seed, seed_queue):
        """
        Perform splice mutation followed by havoc mutations.
        
        Args:
            seed: Current seed to mutate
            seed_queue: List of available seeds for splicing
            
        Notes:
            - Falls back to havoc mutation if splicing not possible
            - Ensures different seeds are selected for splicing
            - Applies havoc mutations after splicing
        """
        if len(seed_queue) < 2:
            return self.havoc_mutator.mutate(seed)
            
        # Select another seed randomly (not the same one)
        other_seeds = [s for s in seed_queue if s.seed_id != seed.seed_id]
        other_seed = random.choice(other_seeds)
        
        # Read both seeds
        with open(seed.path, 'rb') as f:
            data1 = bytearray(f.read())
        with open(other_seed.path, 'rb') as f:
            data2 = bytearray(f.read())
            
        if len(data1) < 4 or len(data2) < 4:
            return self.havoc_mutator.mutate(seed)
            
        # Select splice points
        split_point1 = random.randint(1, len(data1) - 2)
        split_point2 = random.randint(1, len(data2) - 2)
        
        # Create spliced data
        spliced_data = data1[:split_point1] + data2[split_point2:]
        
        # Write spliced data
        with open(self.conf['current_input'], 'wb') as f:
            f.write(spliced_data)
            
        # Apply havoc mutations to spliced data
        self.havoc_mutator.mutate(seed)

class MutationStrategy:
    """
    Manages mutation operator selection using epsilon-greedy strategy.
    
    This class:
    1. Tracks performance of different mutation operators
    2. Selects between operators based on their effectiveness
    3. Balances exploration and exploitation
    """
    
    def __init__(self, conf):
        """
        Initialize mutation strategy.
        
        Args:
            conf (dict): Configuration dictionary
        """
        self.havoc_mutator = HavocMutator(conf)
        self.splice_mutator = SpliceMutator(conf)
        self.epsilon = 0.1  # Exploration rate
        
        # Performance tracking
        self.havoc_rewards = 0
        self.splice_rewards = 0
        self.havoc_uses = 0
        self.splice_uses = 0
        self.havoc_crashes = 0
        self.splice_crashes = 0
        
    def select_operator(self):
        """
        Select mutation operator using epsilon-greedy strategy.
        
        Returns:
            str: Selected operator ('havoc' or 'splice')
            
        Notes:
            - Epsilon chance of random selection (exploration)
            - Otherwise selects best performing operator (exploitation)
            - Performance includes both coverage and crashes
        """
        if random.random() < self.epsilon:
            return random.choice(['havoc', 'splice'])
            
        # Calculate scores considering both coverage and crashes
        havoc_score = (self.havoc_rewards + self.havoc_crashes * 10) / max(1, self.havoc_uses)
        splice_score = (self.splice_rewards + self.splice_crashes * 10) / max(1, self.splice_uses)
        
        return 'havoc' if havoc_score >= splice_score else 'splice'
        
    def update_rewards(self, operator, new_coverage, crashed=False):
        """
        Update operator statistics based on results.
        
        Args:
            operator (str): Operator used ('havoc' or 'splice')
            new_coverage (int): Amount of new coverage found
            crashed (bool): Whether the input caused a crash
        """
        if operator == 'havoc':
            self.havoc_uses += 1
            self.havoc_rewards += new_coverage
            if crashed:
                self.havoc_crashes += 1
        else:
            self.splice_uses += 1
            self.splice_rewards += new_coverage
            if crashed:
                self.splice_crashes += 1

def havoc_mutation(conf, seed):
    """Main mutation function"""
    mutator = HavocMutator(conf)
    mutator.mutate(seed)