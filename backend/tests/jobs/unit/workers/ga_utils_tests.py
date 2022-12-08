"""Tests for ga_utils."""

import json
import os
import textwrap
from unittest import mock

from absl.testing import absltest
from absl.testing import parameterized
from google import auth
from google.auth import credentials
from google.cloud import bigquery
from googleapiclient import discovery
from googleapiclient import http

from common import crmint_logging
from jobs.workers.ga import ga_utils
from tests import utils

DATA_DIR = os.path.join(os.path.dirname(__file__), '../../../data')

_SAMPLE_TEMPLATE_v3 = textwrap.dedent("""\
    {
      "name": "${name}",
      "linkedViews": ["${linked_view}"]
    }""")


def _datafile(filename):
  return os.path.join(DATA_DIR, filename)


def _read_datafile(filename):
  with open(_datafile(filename), 'rb') as f:
    content = f.read()
  return content


class GoogleAnalyticsUtilsTest(parameterized.TestCase):

  def setUp(self):
    super().setUp()
    self.http_v3 = http.HttpMock(
        _datafile('google_analytics_v3.json'),
        headers={'status': '200'})
    self.http_v1alpha = http.HttpMock(
        _datafile('google_analytics_admin_v1alpha.json'),
        headers={'status': '200'})
    self.patched_log_message = self.enter_context(
        mock.patch.object(crmint_logging, 'log_global_message', autospec=True))

  @parameterized.parameters(
      ('analytics', 'v3',
       'https://analytics.googleapis.com/analytics/v3/'),
      ('analyticsreporting', 'v4',
       'https://analyticsreporting.googleapis.com/'),
      ('analyticsadmin', 'v1alpha',
       'https://analyticsadmin.googleapis.com/'),
  )
  def test_get_client_with_version(self, service, version, api_base_url):
    mock_credentials = mock.create_autospec(
        credentials.Credentials, instance=True, spec_set=True)
    self.enter_context(
        mock.patch.object(
            auth,
            'default',
            autospec=True,
            spec_set=True,
            return_value=(mock_credentials, None)))
    client = ga_utils.get_client(service, version)
    self.assertEqual(client._baseUrl, api_base_url)

  def test_get_dataimport_upload_status_pending(self):
    # Response does not contain yet an upload item.
    response = {
        'kind': 'analytics#uploads',
        'totalResults': 1,
        'startIndex': 1,
        'itemsPerPage': 1000,
        'items': [],
    }
    request_builder = http.RequestMockBuilder(
        {'analytics.management.uploads.list': (None, json.dumps(response))})
    client = ga_utils.get_client(
        'analytics', 'v3', http=self.http_v3, request_builder=request_builder)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    upload_status = ga_utils.get_dataimport_upload_status(client, dataimport)
    self.assertEqual(upload_status, ga_utils.UploadStatus.PENDING)

  def test_get_dataimport_upload_status_completed(self):
    response = {
        'kind': 'analytics#uploads',
        'totalResults': 1,
        'startIndex': 1,
        'itemsPerPage': 1000,
        'items': [
            {
                'id': '5qan4As6S7WgAa',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-23T10:00:54.822Z',
                'errors': [],
            }
        ],
    }
    request_builder = http.RequestMockBuilder(
        {'analytics.management.uploads.list': (None, json.dumps(response))})
    client = ga_utils.get_client(
        'analytics', 'v3', http=self.http_v3, request_builder=request_builder)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    upload_status = ga_utils.get_dataimport_upload_status(client, dataimport)
    self.assertEqual(upload_status, ga_utils.UploadStatus.COMPLETED)

  @parameterized.named_parameters(
      ('Deleted All', None, ['5qan4As6S7WgAa', 'qmcaotljicrpdw']),
      ('Keep most recent upload', 1, ['5qan4As6S7WgAa']),
      ('Keep 2 most recent uploads', 2, []),
  )
  def test_delete_all_uploads(self, max_to_keep, expected_deleted_ids):
    response = {
        'kind': 'analytics#uploads',
        'totalResults': 1,
        'startIndex': 1,
        'itemsPerPage': 1000,
        'items': [
            {
                'id': 'qmcaotljicrpdw',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-24T10:00:54.822Z',
                'errors': [],
            },
            {
                'id': '5qan4As6S7WgAa',
                'kind': 'analytics#upload',
                'accountId': '127959147',
                'customDataSourceId': 'elD5IH29Toqgc1vzzHFUrw',
                'status': 'PENDING',
                'uploadTime': '2022-05-23T10:00:54.822Z',
                'errors': [],
            },
        ],
    }
    request_builder = http.RequestMockBuilder(
        {'analytics.management.uploads.list': (None, json.dumps(response))})
    client = ga_utils.get_client(
        'analytics', 'v3', http=self.http_v3, request_builder=request_builder)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    deleted_ids = ga_utils.delete_oldest_uploads(
        client, dataimport, max_to_keep=max_to_keep)
    self.assertCountEqual(deleted_ids, expected_deleted_ids)

  @parameterized.named_parameters(
      ('Raises ValueError for negative value', -1),
      ('Raises ValueError for zero', 0),
  )
  def test_delete_all_uploads_with_bad_max_to_keep(self, max_to_keep):
    with self.assertRaisesRegex(ValueError,
                                'Invalid value for argument `max_to_keep`.'):
      ga_utils.delete_oldest_uploads(
          mock.ANY, mock.ANY, max_to_keep=max_to_keep)

  def test_upload_dataimport_without_progress_callback(self):
    ga_api_discovery_file = _datafile('google_analytics_v3.json')
    with open(ga_api_discovery_file, 'rb') as f:
      ga_api_discovery_content = f.read()
    http_seq = http.HttpMockSequence(
        [
            # Location response, since it's a resumable upload
            ({'status': '200',
              'location': 'http://upload.example.com/1'}, b'{}'),
            # Upload by chunk responses
            ({'status': '308', 'range': 'bytes 0-9'}, b'{}'),
            ({'status': '308', 'range': 'bytes 0-19'}, b'{}'),
            ({'status': '200'}, b'{}'),
        ]
    )
    client = discovery.build_from_document(
        service=ga_api_discovery_content, http=http_seq)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    # `create_tempfile` needs access to --test_tmpdir, however in the OSS world
    # pytest doesn't run `absltest.main`, so we need to init flags ourselves.
    utils.initialize_flags_with_defaults()
    csv_file = self.create_tempfile(
        content=textwrap.dedent("""\
            UserId,Score
            123,0.5
            456,0.8"""))
    ga_utils.upload_dataimport(
        client,
        dataimport,
        csv_file.full_path,
        chunksize=10)  # Leads to 3 requests since our content is 28 bytes long.
    self.assertEmpty(http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')

  def test_upload_dataimport_with_progress_callback(self):
    ga_api_discovery_file = _datafile('google_analytics_v3.json')
    with open(ga_api_discovery_file, 'rb') as f:
      ga_api_discovery_content = f.read()
    http_seq = http.HttpMockSequence(
        [
            # Location response, since it's a resumable upload
            ({'status': '200',
              'location': 'http://upload.example.com/1'}, b'{}'),
            # Upload by chunk responses
            ({'status': '308', 'range': 'bytes 0-9'}, b'{}'),
            ({'status': '308', 'range': 'bytes 0-19'}, b'{}'),
            ({'status': '200'}, b'{}'),
        ]
    )
    client = discovery.build_from_document(
        service=ga_api_discovery_content, http=http_seq)
    dataimport = ga_utils.DataImportReference(
        account_id='123',
        property_id='UA-456-7',
        dataset_id='elD5IH29Toqgc1vzzHFUrw')
    # `create_tempfile` needs access to --test_tmpdir, however in the OSS world
    # pytest doesn't run `absltest.main`, so we need to init flags ourselves.
    utils.initialize_flags_with_defaults()
    csv_file = self.create_tempfile(
        content=textwrap.dedent("""\
            UserId,Score
            123,0.5
            456,0.8"""))
    mock_progress_callback = mock.Mock()
    ga_utils.upload_dataimport(
        client,
        dataimport,
        csv_file.full_path,
        chunksize=10,  # Leads to 3 requests since our content is 28 bytes long.
        progress_callback=mock_progress_callback)
    self.assertEmpty(http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')
    self.assertSequenceEqual(
        (
            mock.call(0.3571),
            mock.call(0.7143),
            mock.call(1.0),
        ),
        mock_progress_callback.mock_calls,
    )

  def test_fetch_audiences_with_two_pages_result(self):
    ga_api_discovery_file = _datafile('google_analytics_v3.json')
    with open(ga_api_discovery_file, 'rb') as f:
      ga_api_discovery_content = f.read()
    http_seq = http.HttpMockSequence([
        # Page 1
        ({'status': '200'},
         _read_datafile(
             'analytics.management.remarketingAudience.list.page1.json')),
        # Page 2
        ({'status': '200'},
         _read_datafile(
             'analytics.management.remarketingAudience.list.page2.json')),
    ])
    client = discovery.build_from_document(
        service=ga_api_discovery_content, http=http_seq)
    audiences_map = ga_utils.fetch_audiences(client, '123456', 'UA-123456-2')
    self.assertEmpty(http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')
    self.assertCountEqual(list(audiences_map.keys()),
                          ['New Visitors', 'All Users'])

  def test_get_audience_operations(self):
    patches = [
        ga_utils.AudiencePatch({'name': 'abc', 'a': 1, 'b': 2}),
        ga_utils.AudiencePatch({'name': 'def', 'a': 1}),
    ]
    audiences = {
        'foo': ga_utils.Audience({'id': '123', 'name': 'foo', 'd': 4}),
        'abc': ga_utils.Audience({'id': '456', 'name': 'abc', 'a': 1, 'c': 3}),
    }
    self.assertCountEqual(
        ga_utils.get_audience_operations(patches, audiences),
        (
            ga_utils.AudienceOperationUpdate(
                id='456',
                data=ga_utils.AudiencePatch({'name': 'abc', 'a': 1, 'b': 2})),
            ga_utils.AudienceOperationInsert(
                data=ga_utils.AudiencePatch({'name': 'def', 'a': 1})),
        )
    )

  def test_run_audience_operations(self):
    request_builder = http.RequestMockBuilder(
        {
            'analytics.management.remarketingAudience.insert': (None, b'{}'),
            'analytics.management.remarketingAudience.patch': (None, b'{}'),
        })
    client = ga_utils.get_client(
        'analytics', 'v3', http=self.http_v3, request_builder=request_builder)
    operations = [
        ga_utils.AudienceOperationUpdate(
            id='456',
            data=ga_utils.AudiencePatch({'name': 'abc', 'a': 1, 'b': 2})),
        ga_utils.AudienceOperationInsert(
            data=ga_utils.AudiencePatch({'name': 'def', 'a': 1})),
    ]
    logger = mock.Mock()
    ga_utils.run_audience_operations(
        client, '123456', 'UA-123456-2', operations, logger)
    self.assertSequenceEqual(
        [
            mock.call('Updating existing audience for id: 456'),
            mock.call('Inserting new audience'),
        ],
        logger.mock_calls,
    )

  def test_run_audience_operations_raises_error(self):
    """Raises a ValueError on a new unsupported operation type."""

    class AudienceOperationDelete(ga_utils.AudienceOperationBase):
      pass

    client = ga_utils.get_client('analytics', 'v3', http=self.http_v3)
    operations = [AudienceOperationDelete()]
    with self.assertRaisesRegex(ValueError, 'Unsupported operation'):
      ga_utils.run_audience_operations(
          client, '123456', 'UA-123456-2', operations)

  def test_fetch_audiences_ga4_with_two_pages_result(self):
    ga_api_discovery_file = _datafile('google_analytics_admin_v1alpha.json')
    with open(ga_api_discovery_file, 'rb') as f:
      ga_api_discovery_content = f.read()
    http_seq = http.HttpMockSequence([
        # Page 1
        ({'status': '200'},
         _read_datafile(
             'analyticsadmin.properties.audiences.list.page1.json')),
        # Page 2
        ({'status': '200'},
         _read_datafile(
             'analyticsadmin.properties.audiences.list.page2.json')),
    ])
    client = discovery.build_from_document(
        service=ga_api_discovery_content, http=http_seq)
    audiences_map = ga_utils.fetch_audiences_ga4(client, '123456')
    self.assertEmpty(http_seq._iterable,
                     msg='The sequence of HttpMock should be empty, indicating '
                         'that we handled all the chunks as expected.')
    print(audiences_map.keys())
    self.assertCountEqual(
        list(audiences_map.keys()),
        [
            'Top download_training_pipeline Users > 500',
            'All Users',
            'Purchasers',
            'New Visitors',
        ])

  def test_get_audience_operations_ga4(self):
    patches = [
        ga_utils.AudiencePatch({
            'displayName': 'FOO',
            'description': 'Some description',
            'membershipDurationDays': 4,
            'filterClauses': [],
        }),
        ga_utils.AudiencePatch({
            'displayName': 'ABC',
            'description': 'Some description updated',
            'membershipDurationDays': 2,
            'filterClauses': [],
        }),
        ga_utils.AudiencePatch({
            'displayName': 'DEF',
            'description': 'Some description',
            'membershipDurationDays': 1,
            'filterClauses': [],
        }),
    ]
    audiences = {
        'ABC': ga_utils.Audience({
            'name': 'abc',
            'displayName': 'ABC',
            'description': 'Some description',
            'membershipDurationDays': 2,
            'filterClauses': [],
        }),
        'DEF': ga_utils.Audience({
            'name': 'def',
            'displayName': 'DEF',
            'description': 'Some description',
            'membershipDurationDays': 1,
            'filterClauses': [],
        }),
    }
    self.assertCountEqual(
        ga_utils.get_audience_operations_ga4(patches, audiences),
        (
            ga_utils.AudienceOperationUpdate(
                id='abc',
                data=ga_utils.AudiencePatch({
                    'displayName': 'ABC',
                    'description': 'Some description updated',
                })),
            ga_utils.AudienceOperationInsert(
                data=ga_utils.AudiencePatch({
                    'displayName': 'FOO',
                    'description': 'Some description',
                    'membershipDurationDays': 4,
                    'filterClauses': [],
                })),
        )
    )

  def test_get_audience_operations_ga4_logs_warning_immutable(self):
    """Logs a warning when immutable fields are not matching."""
    patches = [
        ga_utils.AudiencePatch({
            'displayName': 'FOO',
            'description': 'Some description',
            'membershipDurationDays': 4,
            'filterClauses': [],
        }),
    ]
    audiences = {
        'FOO': ga_utils.Audience({
            'name': 'foo',
            'displayName': 'FOO',
            'description': 'Some description',
            'membershipDurationDays': 3,
            'filterClauses': [],
        }),
    }
    _ = ga_utils.get_audience_operations_ga4(patches, audiences)
    self.patched_log_message.assert_called_once_with(
        mock.ANY, log_level='WARNING')

  def test_run_audience_operations_ga4(self):
    request_builder = http.RequestMockBuilder(
        {
            'analytics.management.remarketingAudience.insert': (None, b'{}'),
            'analytics.management.remarketingAudience.patch': (None, b'{}'),
        })
    client = ga_utils.get_client(
        'analyticsadmin',
        'v1alpha',
        http=self.http_v1alpha,
        request_builder=request_builder)
    operations = [
        ga_utils.AudienceOperationUpdate(
            id='properties/123456/audiences/abc',
            data=ga_utils.AudiencePatch(
                {
                    'name': 'properties/123456/audiences/abc',
                    'displayName': 'ABC',
                    'a': 1,
                    'b': 2
                })),
        ga_utils.AudienceOperationInsert(
            data=ga_utils.AudiencePatch({'name': 'def', 'a': 1})),
    ]
    logger = mock.Mock()
    ga_utils.run_audience_operations_ga4(client, '123456', operations, logger)
    self.assertSequenceEqual(
        [
            mock.call('Updating existing audience for name: ABC and '
                      'resource: properties/123456/audiences/abc'),
            mock.call('Inserting new audience'),
        ],
        logger.mock_calls,
    )

  def test_run_audience_operations_ga4_raises_error(self):
    """Raises a ValueError on a new unsupported operation type."""

    class AudienceOperationDelete(ga_utils.AudienceOperationBase):
      pass

    client = ga_utils.get_client(
        'analyticsadmin', 'v1alpha', http=self.http_v1alpha)
    operations = [AudienceOperationDelete()]
    with self.assertRaisesRegex(ValueError, 'Unsupported operation'):
      ga_utils.run_audience_operations_ga4(client, '123456', operations)

  @parameterized.named_parameters(
      ('web',
       'G-4703L87M1F', 'measurement_id'),
      ('android',
       '1:1007872300143:android:f90da822e4fb9bf81c299a', 'firebase_app_id'),
      ('ios',
       '1:1007872300143:ios:94ab6bfcec7c91311c299a', 'firebase_app_id'),
  )
  def test_get_url_param_by_id_with_variations(
      self, measurement_id, expected_url_param):
    url_param = ga_utils.get_url_param_by_id(measurement_id)
    self.assertEqual(url_param, expected_url_param)

  @parameterized.named_parameters(
      ('web_less_than_10_characters', 'G-4703L87M1'),
      ('web_uses_ua_tracking_id', 'UA-1234567-8'),
      ('android_not_found', '1:1007872300143:windows:f90da822e4fb9bf81c299a'),
      ('ios_not_found', '1:1007872300143:blackberry:94ab6bfcec7c91311c299a'),
  )
  def test_get_url_param_by_id_raises_error_with_variations(
      self, measurement_id):
    """Raises a ValueError on unsupported GA4 measurement IDs."""
    with self.assertRaisesRegex(
        ValueError, 'Unsupported Measurement ID/Firebase App ID'):
      ga_utils.get_url_param_by_id(measurement_id)

  def test_get_audience_patches(self):
    bq_client = mock.create_autospec(
        bigquery.Client, instance=True, spec_set=True)
    bq_client.list_rows.return_value = [
        {
            'name': 'foo',
            'linked_view': 'abc',
        },
        {
            'name': 'bar',
            'linked_view': 'xyz',
        },
    ]
    table_ref = bigquery.TableReference.from_string(
        'DATASET.output_table', 'PROJECT')
    template = _SAMPLE_TEMPLATE_v3
    patches = ga_utils.get_audience_patches(bq_client, table_ref, template)
    self.assertSequenceEqual(
        patches,
        [
            ga_utils.Audience({
                'name': 'foo',
                'linkedViews': ['abc']
            }),
            ga_utils.Audience({
                'name': 'bar',
                'linkedViews': ['xyz']
            }),
        ])

  @parameterized.named_parameters(
      ('parameter_longer_than_24_chars', 'a' * 25, 'USER', 'ValidDisplayName',
       False, 'ValidDescription'),
      ('parameter_longer_than_40_chars', 'a' * 41, 'EVENT', 'ValidDisplayName',
       False, 'ValidDescription'),
      ('display_longer_than_82_chars', 'ValidParameter', 'USER',
       'a' * 83, False, 'ValidDescription'),
      ('description_longer_than_150_chars', 'ValidParameter', 'USER',
       'ValidDisplayName', False, 'a' * 151),
  )
  def test_create_custom_dimension_ga4_raises_error_with_variations(
      self, parameter_name, scope, display_name, disallow_ads_personalization,
      description):
    """Raises a ValueError on Custom Dimension limits."""
    ga_client = ga_utils.get_client(
        'analyticsadmin', 'v1alpha', http=self.http_v1alpha)
    ga_property_id = '123456789'
    with self.assertRaisesRegex(
        ValueError,
        '(Parameter Name|Display Name|Description) can '
        'be (24|40|82|150) characters maximum.'):
      ga_utils.create_custom_dimension_ga4(ga_client, ga_property_id,
                                           parameter_name, scope, display_name,
                                           disallow_ads_personalization,
                                           description)

  def test_create_custom_dimension_ga4_raises_error_invalid_scope(self):
    """Raises a ValueError on Custom Dimension invalid scope."""
    ga_client = ga_utils.get_client(
        'analyticsadmin', 'v1alpha', http=self.http_v1alpha)
    ga_property_id = '123456789'
    parameter_name = 'ValidParameter'
    scope = 'INVALIDSCOPE'
    display_name = 'ValidDisplayName'
    disallow_ads_personalization = False
    description = 'ValidDescription'
    with self.assertRaisesRegex(
        ValueError, 'Scope must be either USER or EVENT.'):
      ga_utils.create_custom_dimension_ga4(ga_client, ga_property_id,
                                           parameter_name, scope, display_name,
                                           disallow_ads_personalization,
                                           description)


if __name__ == '__main__':
  absltest.main()
