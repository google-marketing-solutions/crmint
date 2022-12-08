"""Tests for ga_custom_dimension_creator_ga4."""

import os

from unittest import mock

from absl.testing import absltest
from google.auth import credentials
from googleapiclient import http
import httplib2

from jobs.workers.ga import ga_custom_dimension_creator_ga4
from jobs.workers.ga import ga_utils

DATA_DIR = os.path.join(os.path.dirname(__file__), '../../../data')


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


def _make_credentials():
  return mock.create_autospec(
      credentials.Credentials, instance=True, spec_set=True)


class TestGA4CustomDimensionCreator(absltest.TestCase):

  def setUp(self):
    super().setUp()
    self.http_v1alpha = http.HttpMock(
        _datafile('google_analytics_admin_v1alpha.json'),
        headers={'status': '200'})

  def test_create_new_custom_dimension(self):
    request_builder = http.RequestMockBuilder({
        'analyticsadmin.properties.customDimensions.create': (None, b'{}'),
    })
    ga_client = ga_utils.get_client(
        'analyticsadmin', 'v1alpha',
        http=self.http_v1alpha, request_builder=request_builder)
    mock_get_client = self.enter_context(
        mock.patch.object(
            ga_utils, 'get_client', autospec=True, return_value=ga_client))
    worker_inst = ga_custom_dimension_creator_ga4.GA4CustomDimensionCreator(
        {
            'ga_property_id': '123456789',
            'display_name': 'DISPLAY_NAME',
            'parameter_name': 'PARAMETER_NAME',
            'scope': 'USER',
            'description': 'DESCRIPTION',
            'disallow_ads_personalization': False
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    patched_logger = self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    worker_inst.execute()
    mock_get_client.assert_called_once_with('analyticsadmin', 'v1alpha')
    self.assertSequenceEqual(
        [
            mock.call(mock.ANY),
            mock.call('Inserting new custom dimension.'),
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )

  def test_catches_409_if_custom_dimension_already_exists(self):
    response = httplib2.Response({'status': 409})
    request_builder = http.RequestMockBuilder({
        'analyticsadmin.properties.customDimensions.create': (response, b'{}'),
    })
    ga_client = ga_utils.get_client(
        'analyticsadmin', 'v1alpha',
        http=self.http_v1alpha, request_builder=request_builder)
    mock_get_client = self.enter_context(
        mock.patch.object(
            ga_utils, 'get_client', autospec=True, return_value=ga_client))
    worker_inst = ga_custom_dimension_creator_ga4.GA4CustomDimensionCreator(
        {
            'ga_property_id': '123456789',
            'display_name': 'DISPLAY_NAME',
            'parameter_name': 'PARAMETER_NAME',
            'scope': 'USER',
            'description': 'DESCRIPTION',
            'disallow_ads_personalization': False
        },
        pipeline_id=1,
        job_id=1,
        logger_project='PROJECT',
        logger_credentials=_make_credentials())
    patched_logger = self.enter_context(
        mock.patch.object(worker_inst, 'log_info', autospec=True))
    worker_inst.execute()
    mock_get_client.assert_called_once_with('analyticsadmin', 'v1alpha')
    self.assertSequenceEqual(
        [
            mock.call(mock.ANY),
            mock.call('Inserting new custom dimension.'),
            mock.call('Requested parameter name already exists. '
                      'No changes made.'),
            mock.call('Finished successfully'),
        ],
        patched_logger.mock_calls
    )


if __name__ == '__main__':
  absltest.main()
