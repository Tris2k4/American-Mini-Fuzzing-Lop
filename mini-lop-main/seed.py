import os

class Seed:
    def __init__(self, path, seed_id, coverage, exec_time):
        self.path = path
        self.seed_id = seed_id
        self.coverage = coverage  # Set of edges covered by this seed
        self.exec_time = exec_time
        self.file_size = os.path.getsize(path)
        # By default, a seed is not marked as favored
        self.favored = False

    def mark_favored(self):
        self.favored = True

    def unmark_favored(self):
        self.favored = False

    def get_valuation(self):
        # Valuation used for sorting (execution time * file size)
        return self.exec_time * self.file_size
