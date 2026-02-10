"""
Generate ERD diagram for the database models.
"""
import sys
sys.path.insert(0, '/Users/macbookpr0/SN Mac Drive/5-WORKS/ChoyOperator/ChoyOperator')

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, List

import erdantic as erd
from src.data.models import Account, ScheduledPost, LogEntry, PostStatusEnum


# Create diagram
diagram = erd.create(Account, ScheduledPost, LogEntry)

# Draw to file
diagram.draw("database_erd.png")
print("ERD diagram saved to database_erd.png")

# Also output as DOT format for manual editing
dot_content = diagram.to_dot()
with open("database_erd.dot", "w") as f:
    f.write(dot_content)
print("DOT file saved to database_erd.dot")
