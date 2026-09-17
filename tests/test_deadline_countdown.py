import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import server


NOW = datetime(2026, 9, 17, 23, 0, 0, tzinfo=timezone.utc)


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


class DeadlineCountdownTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(server, "datetime", FrozenDatetime)
        clock.start()
        self.addCleanup(clock.stop)

    def test_future_deadline_with_eastern_offset(self):
        result = server.deadline_countdown("2026-09-18T21:03:04-04:00")
        self.assertEqual(result["status"], "upcoming")
        self.assertEqual(
            [result[key] for key in ("days", "hours", "minutes", "seconds")],
            [1, 2, 3, 4],
        )
        self.assertEqual(result["checked_at"], NOW.isoformat())
        self.assertEqual(result["deadline"], "2026-09-18T21:03:04-04:00")

    def test_equivalent_offsets_have_the_same_countdown(self):
        eastern = server.deadline_countdown("2026-09-18T21:03:04-04:00")
        utc = server.deadline_countdown("2026-09-19T01:03:04Z")
        east_of_utc = server.deadline_countdown("2026-09-19T06:33:04+05:30")
        for key in ("status", "days", "hours", "minutes", "seconds"):
            self.assertEqual(eastern[key], utc[key])
            self.assertEqual(east_of_utc[key], utc[key])

    def test_overdue_deadline(self):
        result = server.deadline_countdown("2026-09-16T20:56:56Z")
        self.assertEqual(result["status"], "overdue")
        self.assertEqual(
            [result[key] for key in ("days", "hours", "minutes", "seconds")],
            [1, 2, 3, 4],
        )
        self.assertTrue(result["message"].startswith("Overdue by:"))

    def test_exact_deadline(self):
        result = server.deadline_countdown("2026-09-17T23:00:00Z")
        self.assertEqual(result["status"], "due_now")
        self.assertEqual(result["message"], "The deadline is now.")

    def test_subminute_deadlines_preserve_direction(self):
        for timestamp, status in [
            ("2026-09-17T23:00:30Z", "upcoming"),
            ("2026-09-17T22:59:30Z", "overdue"),
        ]:
            with self.subTest(timestamp=timestamp):
                result = server.deadline_countdown(timestamp)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["minutes"], 0)
                self.assertEqual(result["seconds"], 30)

    def test_fractional_seconds_are_not_reported_as_due_now(self):
        for timestamp, status in [
            ("2026-09-17T23:00:00.5Z", "upcoming"),
            ("2026-09-17T22:59:59.5Z", "overdue"),
        ]:
            with self.subTest(timestamp=timestamp):
                result = server.deadline_countdown(timestamp)
                self.assertEqual(result["status"], status)
                self.assertIn("less than 1 second", result["message"])

    def test_missing_timezone_is_rejected(self):
        for timestamp in ("2026-09-18T23:59:00", "2026-09-18"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaisesRegex(ValueError, "timezone"):
                    server.deadline_countdown(timestamp)

    def test_invalid_dates_are_rejected(self):
        for timestamp in ("", "Friday night", "2026-02-30T23:59:00Z"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaisesRegex(ValueError, "Invalid deadline"):
                    server.deadline_countdown(timestamp)


if __name__ == "__main__":
    unittest.main()
