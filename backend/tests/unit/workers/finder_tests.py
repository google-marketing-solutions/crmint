"""Tests for the find method in workers.__init__."""

from absl.testing import absltest

from jobs.workers import finder
from jobs.workers.bigquery import bq_query_launcher
from jobs.workers.bigquery import bq_to_measurement_protocol_ga4


class FindWorkerClassTest(absltest.TestCase):

  def test_can_find_worker_class(self):
    worker_class = finder.get_worker_class('BQQueryLauncher')
    self.assertEqual(worker_class,
                     bq_query_launcher.BQQueryLauncher)

  def test_can_find_worker_class_with_lowercase_typo(self):
    worker_class = finder.get_worker_class('BQtomeasurementprotocolGA4')
    self.assertEqual(worker_class,
                     bq_to_measurement_protocol_ga4.BQToMeasurementProtocolGA4)

  def test_raises_on_unknown_worker(self):
    with self.assertRaises(ModuleNotFoundError):
      finder.get_worker_class('UnknownWorkerClass')


if __name__ == '__main__':
  absltest.main()
