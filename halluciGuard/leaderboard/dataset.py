# HalluciGuard - AI Hallucination Detection Middleware
# Copyright (C) 2026 HalluciGuard Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Benchmark dataset with ground truth test cases for hallucination detection.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import json
import os


class Category(Enum):
    """Categories for benchmark test cases."""
    GENERAL = "general"
    SCIENCE = "science"
    HISTORY = "history"
    MEDICAL = "medical"
    LEGAL = "legal"
    CODE = "code"
    MATH = "math"
    GEOGRAPHY = "geography"


@dataclass
class BenchmarkCase:
    """
    A single benchmark test case with ground truth.
    
    Attributes:
        id: Unique identifier for the test case
        prompt: The question/prompt to send to the LLM
        category: The category this test case belongs to
        ground_truth_facts: List of facts that MUST appear in a correct answer
        common_hallucinations: List of common incorrect facts LLMs often generate
        difficulty: 1-5 scale of difficulty
        source: Source of the ground truth (for verification)
    """
    id: str
    prompt: str
    category: Category
    ground_truth_facts: List[str]
    common_hallucinations: List[str] = field(default_factory=list)
    difficulty: int = 3
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "category": self.category.value,
            "ground_truth_facts": self.ground_truth_facts,
            "common_hallucinations": self.common_hallucinations,
            "difficulty": self.difficulty,
            "source": self.source,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BenchmarkCase":
        return cls(
            id=data["id"],
            prompt=data["prompt"],
            category=Category(data["category"]),
            ground_truth_facts=data["ground_truth_facts"],
            common_hallucinations=data.get("common_hallucinations", []),
            difficulty=data.get("difficulty", 3),
            source=data.get("source", ""),
        )


class BenchmarkDataset:
    """
    A collection of benchmark test cases with ground truth.
    """
    
    def __init__(self, cases: Optional[List[BenchmarkCase]] = None):
        self.cases = cases or []
    
    def add_case(self, case: BenchmarkCase):
        self.cases.append(case)
    
    def get_by_category(self, category: Category) -> List[BenchmarkCase]:
        return [c for c in self.cases if c.category == category]
    
    def get_by_difficulty(self, min_diff: int = 1, max_diff: int = 5) -> List[BenchmarkCase]:
        return [c for c in self.cases if min_diff <= c.difficulty <= max_diff]
    
    def to_json(self) -> str:
        return json.dumps({
            "version": "1.0",
            "total_cases": len(self.cases),
            "categories": {cat.value: len(self.get_by_category(cat)) for cat in Category},
            "cases": [c.to_dict() for c in self.cases]
        }, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "BenchmarkDataset":
        data = json.loads(json_str)
        cases = [BenchmarkCase.from_dict(c) for c in data.get("cases", [])]
        return cls(cases=cases)
    
    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(self.to_json())
    
    @classmethod
    def load(cls, path: str) -> "BenchmarkDataset":
        with open(path, "r") as f:
            return cls.from_json(f.read())


def get_default_dataset() -> BenchmarkDataset:
    """
    Get the default benchmark dataset with curated test cases.
    
    This dataset covers various categories and difficulty levels,
    designed to expose common LLM hallucination patterns.
    """
    cases = [
        # === SCIENCE ===
        BenchmarkCase(
            id="sci_001",
            prompt="What did Albert Einstein win the Nobel Prize for and in what year?",
            category=Category.SCIENCE,
            ground_truth_facts=[
                "Einstein won the Nobel Prize in Physics in 1921",
                "He won it for the photoelectric effect",
                "He did NOT win it for the theory of relativity"
            ],
            common_hallucinations=[
                "Einstein won the Nobel Prize for relativity",
                "Einstein won the Nobel Prize for E=mc²",
                "Einstein won the Nobel Prize in 1905"
            ],
            difficulty=2,
            source="Nobel Prize official records"
        ),
        BenchmarkCase(
            id="sci_002",
            prompt="Who discovered penicillin and when?",
            category=Category.SCIENCE,
            ground_truth_facts=[
                "Alexander Fleming discovered penicillin",
                "Discovery was in 1928",
                "It was accidental - from mold contamination"
            ],
            common_hallucinations=[
                "Einstein discovered penicillin",
                "Penicillin was discovered in the 1800s",
                "Louis Pasteur discovered penicillin"
            ],
            difficulty=1,
            source="Historical medical records"
        ),
        BenchmarkCase(
            id="sci_003",
            prompt="What is the speed of light in vacuum?",
            category=Category.SCIENCE,
            ground_truth_facts=[
                "Speed of light is approximately 299,792,458 meters per second",
                "Often rounded to 3×10^8 m/s or 300,000 km/s",
                "It is a fundamental constant denoted by 'c'"
            ],
            common_hallucinations=[
                "Speed of light is exactly 300,000,000 m/s",
                "Speed of light is 186,000 miles per second (this is approximate, not exact)"
            ],
            difficulty=2,
            source="NIST physical constants"
        ),
        
        # === HISTORY ===
        BenchmarkCase(
            id="hist_001",
            prompt="When did World War II end and what were the key events?",
            category=Category.HISTORY,
            ground_truth_facts=[
                "WWII ended in 1945",
                "Germany surrendered in May 1945 (V-E Day May 8)",
                "Japan surrendered in September 1945 (V-J Day September 2)",
                "Atomic bombs were dropped on Hiroshima and Nagasaki in August 1945"
            ],
            common_hallucinations=[
                "WWII ended in 1944",
                "WWII ended when Hitler was assassinated",
                "The war ended with the invasion of Berlin in 1943"
            ],
            difficulty=2,
            source="Historical records"
        ),
        BenchmarkCase(
            id="hist_002",
            prompt="Who was the first person to walk on the moon?",
            category=Category.HISTORY,
            ground_truth_facts=[
                "Neil Armstrong was the first person to walk on the moon",
                "This occurred on July 20, 1969",
                "It was during the Apollo 11 mission",
                "Buzz Aldrin was the second person to walk on the moon"
            ],
            common_hallucinations=[
                "Buzz Aldrin was the first person on the moon",
                "The moon landing was in 1968",
                "Yuri Gagarin walked on the moon"
            ],
            difficulty=1,
            source="NASA historical records"
        ),
        BenchmarkCase(
            id="hist_003",
            prompt="When was the Declaration of Independence signed?",
            category=Category.HISTORY,
            ground_truth_facts=[
                "The Declaration of Independence was adopted on July 4, 1776",
                "Most signatures were actually added on August 2, 1776",
                "It was signed by 56 delegates"
            ],
            common_hallucinations=[
                "All signatures were added on July 4, 1776",
                "It was signed in 1775",
                "George Washington signed on July 4th"
            ],
            difficulty=3,
            source="US National Archives"
        ),
        
        # === MEDICAL ===
        BenchmarkCase(
            id="med_001",
            prompt="What causes the common cold?",
            category=Category.MEDICAL,
            ground_truth_facts=[
                "The common cold is caused by viruses",
                "Rhinoviruses are the most common cause",
                "There are over 200 different viruses that can cause colds",
                "Antibiotics do not work against colds because they are viral, not bacterial"
            ],
            common_hallucinations=[
                "Cold weather directly causes colds",
                "Antibiotics can cure the common cold",
                "There is a single virus that causes all colds"
            ],
            difficulty=2,
            source="CDC and medical literature"
        ),
        BenchmarkCase(
            id="med_002",
            prompt="What is the recommended daily water intake for adults?",
            category=Category.MEDICAL,
            ground_truth_facts=[
                "There is no single universally agreed recommendation",
                "Common guidance suggests around 2-3 liters per day",
                "Needs vary by individual, activity level, and climate",
                "The '8 glasses a day' rule is not scientifically proven"
            ],
            common_hallucinations=[
                "Everyone must drink exactly 8 glasses of water daily",
                "The exact amount is 64 ounces for all adults",
                "Coffee and tea don't count toward daily fluid intake"
            ],
            difficulty=3,
            source="Mayo Clinic and NIH"
        ),
        
        # === GEOGRAPHY ===
        BenchmarkCase(
            id="geo_001",
            prompt="What is the capital of Australia?",
            category=Category.GEOGRAPHY,
            ground_truth_facts=[
                "Canberra is the capital of Australia",
                "It is located in the Australian Capital Territory",
                "Canberra became the capital in 1913"
            ],
            common_hallucinations=[
                "Sydney is the capital of Australia",
                "Melbourne is the capital of Australia"
            ],
            difficulty=2,
            source="Geographical records"
        ),
        BenchmarkCase(
            id="geo_002",
            prompt="What is the largest country by land area?",
            category=Category.GEOGRAPHY,
            ground_truth_facts=[
                "Russia is the largest country by land area",
                "Russia covers approximately 17 million square kilometers",
                "It spans 11 time zones"
            ],
            common_hallucinations=[
                "China is the largest country",
                "Canada is the largest country",
                "The United States is the largest country"
            ],
            difficulty=1,
            source="Geographical records"
        ),
        BenchmarkCase(
            id="geo_003",
            prompt="Which river is the longest in the world?",
            category=Category.GEOGRAPHY,
            ground_truth_facts=[
                "The Nile River is generally considered the longest at approximately 6,650 km",
                "The Amazon River is the second longest at approximately 6,400 km",
                "There is some scientific debate about which is actually longer"
            ],
            common_hallucinations=[
                "The Amazon is definitively the longest river",
                "The Mississippi is the longest river",
                "The Yangtze is the longest river"
            ],
            difficulty=3,
            source="Geographical surveys"
        ),
        
        # === CODE ===
        BenchmarkCase(
            id="code_001",
            prompt="What is the time complexity of binary search?",
            category=Category.CODE,
            ground_truth_facts=[
                "Binary search has O(log n) time complexity",
                "It requires a sorted array",
                "It works by repeatedly dividing the search interval in half"
            ],
            common_hallucinations=[
                "Binary search has O(n) time complexity",
                "Binary search has O(1) time complexity",
                "Binary search works on unsorted arrays"
            ],
            difficulty=2,
            source="Computer science fundamentals"
        ),
        BenchmarkCase(
            id="code_002",
            prompt="What is the difference between HTTP and HTTPS?",
            category=Category.CODE,
            ground_truth_facts=[
                "HTTPS is HTTP with encryption",
                "HTTPS uses TLS/SSL for secure communication",
                "HTTPS uses port 443 by default, HTTP uses port 80",
                "HTTPS provides data integrity and authentication"
            ],
            common_hallucinations=[
                "HTTPS is a completely different protocol from HTTP",
                "HTTPS is only for banking websites",
                "HTTP is deprecated and should never be used"
            ],
            difficulty=1,
            source="Web standards (IETF)"
        ),
        
        # === MATH ===
        BenchmarkCase(
            id="math_001",
            prompt="What is the value of pi?",
            category=Category.MATH,
            ground_truth_facts=[
                "Pi (π) is approximately 3.14159",
                "Pi is an irrational number with infinite decimal places",
                "Pi is the ratio of a circle's circumference to its diameter"
            ],
            common_hallucinations=[
                "Pi is exactly 3.14",
                "Pi is exactly 22/7",
                "Pi has a finite number of decimal places"
            ],
            difficulty=1,
            source="Mathematical constants"
        ),
        BenchmarkCase(
            id="math_002",
            prompt="What is the Fibonacci sequence?",
            category=Category.MATH,
            ground_truth_facts=[
                "Each number is the sum of the two preceding ones",
                "The sequence typically starts with 0 and 1",
                "First few numbers: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34...",
                "Named after Italian mathematician Leonardo of Pisa (Fibonacci)"
            ],
            common_hallucinations=[
                "The sequence starts with 1, 1",
                "Fibonacci invented the sequence (it was known earlier in India)",
                "The sequence is finite"
            ],
            difficulty=2,
            source="Mathematical literature"
        ),
        
        # === LEGAL ===
        BenchmarkCase(
            id="legal_001",
            prompt="What does the First Amendment to the US Constitution protect?",
            category=Category.LEGAL,
            ground_truth_facts=[
                "The First Amendment protects freedom of speech",
                "It also protects freedom of religion",
                "It protects freedom of the press",
                "It protects the right to peaceful assembly",
                "It protects the right to petition the government"
            ],
            common_hallucinations=[
                "The First Amendment protects the right to bear arms (that's the Second)",
                "The First Amendment applies to all speech without exceptions",
                "The First Amendment protects against all government regulation"
            ],
            difficulty=2,
            source="US Constitution"
        ),
        
        # === GENERAL ===
        BenchmarkCase(
            id="gen_001",
            prompt="Who invented the telephone?",
            category=Category.GENERAL,
            ground_truth_facts=[
                "Alexander Graham Bell is credited with inventing the telephone",
                "The first patent was granted in 1876",
                "There were other inventors working on similar technology (Elisha Gray, Antonio Meucci)"
            ],
            common_hallucinations=[
                "Thomas Edison invented the telephone",
                "The telephone was invented in the 20th century",
                "Guglielmo Marconi invented the telephone"
            ],
            difficulty=2,
            source="Historical patent records"
        ),
        BenchmarkCase(
            id="gen_002",
            prompt="What is the chemical formula for water?",
            category=Category.GENERAL,
            ground_truth_facts=[
                "Water's chemical formula is H2O",
                "It consists of two hydrogen atoms and one oxygen atom",
                "Water is essential for all known forms of life"
            ],
            common_hallucinations=[
                "Water's formula is H2O2 (that's hydrogen peroxide)",
                "Water is made of one hydrogen and two oxygen atoms",
                "Water has no chemical formula"
            ],
            difficulty=1,
            source="Chemistry fundamentals"
        ),
        BenchmarkCase(
            id="gen_003",
            prompt="How many planets are in our solar system?",
            category=Category.GENERAL,
            ground_truth_facts=[
                "There are 8 planets in the solar system",
                "Pluto was reclassified as a dwarf planet in 2006",
                "The planets are: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune"
            ],
            common_hallucinations=[
                "There are 9 planets in the solar system",
                "Pluto is still considered a planet",
                "There are 10 planets including Ceres"
            ],
            difficulty=1,
            source="IAU definition (2006)"
        ),
    ]
    
    return BenchmarkDataset(cases=cases)
