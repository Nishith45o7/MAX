"""
Unit tests for Cron Scheduling, Expression Parsing, and Run Logging.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from cron.parser import parse_interval_seconds, matches_cron
from cron.scheduler import CronScheduler
from cron.runner import CronRunner
from brigade_core.storage import StorageManager


class TestCronSuite(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.scheduler = CronScheduler(self.tmp)
        self.storage_mgr = StorageManager(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_interval_parsing(self):
        self.assertEqual(parse_interval_seconds("30s"), 30.0)
        self.assertEqual(parse_interval_seconds("5m"), 300.0)
        self.assertEqual(parse_interval_seconds("2h"), 7200.0)
        self.assertEqual(parse_interval_seconds("1d"), 86400.0)

    def test_cron_matching(self):
        dt = datetime(2026, 6, 4, 9, 30, 0)
        # 30 9 * * * matches 09:30
        self.assertTrue(matches_cron(dt, "30 9 * * *"))
        # 0 9 * * * does not match 09:30
        self.assertFalse(matches_cron(dt, "0 9 * * *"))

    def test_scheduler_lifecycle(self):
        job = self.scheduler.add_job("every", "1h", "Check status")
        self.assertIsNotNone(job.id)
        self.assertEqual(len(self.scheduler.list_jobs()), 1)

        self.scheduler.toggle_job(job.id, False)
        self.assertFalse(self.scheduler.get_job(job.id).enabled)

        self.scheduler.remove_job(job.id)
        self.assertEqual(len(self.scheduler.list_jobs()), 0)

    def test_cron_runner_execution(self):
        executed = []
        runner = CronRunner(
            self.scheduler,
            self.storage_mgr,
            job_executor=lambda j: executed.append(j.id) or "Done"
        )
        job = self.scheduler.add_job("every", "1s", "Fast job")
        runner._execute_job(job)
        self.assertEqual(len(executed), 1)

        # Verify run log written
        run_file = self.storage_mgr.get_cron_run_file(job.id)
        self.assertTrue(run_file.exists())


if __name__ == "__main__":
    unittest.main()
