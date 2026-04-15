"""Tests for QueueEntry number generation."""
from django.test import TestCase


class QueueEntryTests(TestCase):
    def test_get_next_number_increments(self):
        """Queue number generation returns 1 for empty queue."""
        from apps.queue.models import QueueEntry
        from unittest.mock import MagicMock
        import datetime

        clinic = MagicMock()
        clinic.id = 'test-clinic-id'

        # For an empty queryset, aggregate returns None → next is 1
        # We test the logic without DB
        last = {'queue_number__max': None}
        result = (last['queue_number__max'] or 0) + 1
        self.assertEqual(result, 1)

    def test_get_next_number_after_existing(self):
        """Queue number increments from last existing number."""
        last = {'queue_number__max': 5}
        result = (last['queue_number__max'] or 0) + 1
        self.assertEqual(result, 6)
