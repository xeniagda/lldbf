import sys
import os
from abc import ABC, abstractmethod

class Path(ABC):
    @abstractmethod
    def find_path(self):
        pass

    # @abstractmethod
    # def get_contents(self):
    #     pass

class StdLibPath(ABC):
    def __init__(self, path):
        self.path = path

    def find_path(self):
        stdlib_dir = os.path.join(os.path.dirname(__file__), "stdlib")
        return os.path.join(stdlib_dir, self.path)

class LocalPath(ABC):
    def __init__(self, name, bfile):
        self.name = name
        self.base_path = bfile.name

    def find_path(self):
        return os.path.join(os.path.dirname(self.base_path), self.name)

