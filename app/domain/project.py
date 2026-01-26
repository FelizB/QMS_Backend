from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional


@dataclass
class ProjectEntity:
    ProjectId: Optional[int]
    Name: str
    Description: Optional[str]
    Environment: Optional[str]
    Active: bool
    CreationDate: datetime
    StartDate: Optional[date]
    EndDate: Optional[date]
    PercentComplete: Optional[int]

    def mark_complete(self):
        self.PercentComplete = 100

    def archive(self):
        self.Active = False
