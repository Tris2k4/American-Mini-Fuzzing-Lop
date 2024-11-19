Modified/Created Functions:
1 - `SpliceMutator` class in `mutation.py` - New class implementing splice mutation
2 - `MutationStrategy` class - Modified to include epsilon-greedy selection

Implementation Explanation:
Added epsilon-greedy strategy for operator selection:

```python
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

```

The implementation uses:
1 - Epsilon = 0.1 (10% exploration rate)
2 - Exploration: Random operator selection
3 - Exploitation: Select operator with highest average reward
4 - Reward tracking for both coverage and crashes
This epsilon-greedy approach:
1 - Ensures exploration of both operators (10% random selection)
2 - Favors the more successful operator (90% based on performance)
3 - Adapts to changing effectiveness during fuzzing
4 - Balances exploration and exploitation
The strategy helps optimize the use of splice vs havoc mutations based on their success in finding new coverage and crashes.
