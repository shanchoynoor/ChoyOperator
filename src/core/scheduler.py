"""
Scheduler - APScheduler-based task scheduling for posts.

Handles scheduling, persistence, and retry logic for automation tasks.
"""

import logging
from datetime import datetime
from typing import Callable
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    JobExecutionEvent,
)

from src.config import config, PROJECT_ROOT


logger = logging.getLogger(__name__)


class SchedulerManager:
    """
    Manages scheduled automation tasks using APScheduler.
    
    Features:
    - Persistent job storage (survives restarts)
    - Automatic retry on failure
    - Event callbacks for job status updates
    """
    
    def __init__(
        self,
        on_job_executed: Callable[[str, dict], None] | None = None,
        on_job_error: Callable[[str, Exception], None] | None = None,
    ):
        """
        Initialize the scheduler.
        
        Args:
            on_job_executed: Callback when a job completes successfully
            on_job_error: Callback when a job fails
        """
        self.on_job_executed = on_job_executed
        self.on_job_error = on_job_error
        
        # Ensure data directory exists
        db_path = config.database.path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure job stores and executors
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=f"sqlite:///{db_path.parent / 'scheduler.db'}"
            )
        }
        
        executors = {
            "default": ThreadPoolExecutor(max_workers=3)
        }
        
        job_defaults = {
            "coalesce": True,  # Combine missed executions into one
            "max_instances": 1,  # Only one instance per job
            "misfire_grace_time": 60 * 5,  # 5 minutes grace period
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
        )
        
        # Add event listeners
        self.scheduler.add_listener(
            self._on_job_event,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )
        
        self._started = False
    
    def start(self):
        """Start the scheduler."""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler gracefully."""
        if self._started:
            self.scheduler.shutdown(wait=True)
            self._started = False
            logger.info("Scheduler stopped")
    
    def schedule_post(
        self,
        job_id: str,
        run_at: datetime,
        platform: str,
        account_id: int,
        content: str,
        media_paths: list[str] | None = None,
    ) -> str:
        """
        Schedule a post for future execution.
        
        Args:
            job_id: Unique identifier for the job
            run_at: When to execute the job
            platform: Target platform (facebook/twitter/linkedin)
            account_id: Account to post from
            content: Post content
            media_paths: Optional media file paths
            
        Returns:
            Job ID
        """
        from src.core.scheduler_tasks import execute_scheduled_post
        
        self.scheduler.add_job(
            execute_scheduled_post,
            trigger=DateTrigger(run_date=run_at),
            id=job_id,
            replace_existing=True,
            kwargs={
                "platform": platform,
                "account_id": account_id,
                "content": content,
                "media_paths": media_paths or [],
            },
        )
        
        logger.info(f"Scheduled post {job_id} for {run_at}")
        return job_id
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a scheduled job.
        
        Args:
            job_id: Job to cancel
            
        Returns:
            True if job was found and cancelled
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Cancelled job {job_id}")
            return True
        except Exception:
            return False
    
    def get_pending_jobs(self) -> list[dict]:
        """
        Get all pending scheduled jobs.
        
        Returns:
            List of job info dicts
        """
        jobs = self.scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "next_run_time": job.next_run_time,
                "kwargs": job.kwargs,
            }
            for job in jobs
        ]
    
    def reschedule_job(self, job_id: str, new_time: datetime) -> bool:
        """
        Reschedule a job to a new time.
        
        Args:
            job_id: Job to reschedule
            new_time: New execution time
            
        Returns:
            True if rescheduled successfully
        """
        try:
            self.scheduler.reschedule_job(
                job_id,
                trigger=DateTrigger(run_date=new_time)
            )
            logger.info(f"Rescheduled job {job_id} to {new_time}")
            return True
        except Exception:
            return False
    
    def _on_job_event(self, event: JobExecutionEvent):
        """Handle job execution events."""
        job_id = event.job_id
        
        if event.code == EVENT_JOB_EXECUTED:
            logger.info(f"Job {job_id} executed successfully")
            if self.on_job_executed:
                self.on_job_executed(job_id, event.retval)
                
        elif event.code == EVENT_JOB_ERROR:
            logger.error(f"Job {job_id} failed: {event.exception}")
            if self.on_job_error:
                self.on_job_error(job_id, event.exception)
                
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"Job {job_id} was missed")


# Singleton scheduler instance
_scheduler: SchedulerManager | None = None


def get_scheduler() -> SchedulerManager:
    """Get or create the scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerManager()
    return _scheduler
