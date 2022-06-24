"""Utilities for Google Analytics workers."""

import dataclasses
import enum
import functools
import re
from typing import Callable, Mapping, NewType, Optional, Type, TypeVar, Union

from google.api_core import retry
from googleapiclient import discovery
from googleapiclient import http as api_httplib
import httplib2

from common import utils

_MAX_RESULTS_PER_CALL = 100
_NUMBER_OF_RETRIES = 3


def _null_progress_callback(unused_msg: str) -> None:
  """Default progress callback. Used to simplify the tests."""


@functools.cache
def get_client(
    version: str = 'v4',
    http: Optional[Union[httplib2.Http, api_httplib.HttpMock]] = None,
    request_builder: Union[
        Type[api_httplib.HttpRequest],
        api_httplib.RequestMockBuilder] = api_httplib.HttpRequest
) -> discovery.Resource:
  """Configures a client for the Google Analytics API and caches its result.

  Args:
    version: Version of the API to configure the GA client with. Defaults to v4.
    http: Instance of httplib2.Http or something that acts like it that
        HTTP requests will be made through.
    request_builder: Instance of googleapiclient.http.HttpRequest, encapsulator
        for an HTTP request. Especially useful in testing.

  Returns:
    Google Analytics API client of type `googleapiclient.discovery.Resource`.
  """
  service = 'analyticsreporting' if version == 'v4' else 'analytics'
  static_discovery = False if isinstance(http, api_httplib.HttpMock) else None
  return discovery.build(
      service,
      version,
      http=http,
      requestBuilder=request_builder,
      static_discovery=static_discovery)


@dataclasses.dataclass(frozen=True)
class DataImportReference:
  """Encapsulates the identifiers needed to uniquely identify a Data Import.

  More info on the Google Analytics Management API documentation:
  https://developers.google.com/analytics/devguides/config/mgmt/v3/mgmtReference/management/uploads/uploadData
  """
  account_id: str
  property_id: str
  dataset_id: str


@enum.unique
class UploadStatus(enum.Enum):
  PENDING = enum.auto()
  COMPLETED = enum.auto()


def get_dataimport_upload_status(
    client: discovery.Resource,
    dataimport_ref: DataImportReference) -> UploadStatus:
  """Returns the status of a Data Import upload.

  Args:
    client: Google Analytics API client of type
      `googleapiclient.discovery.Resource`.
    dataimport_ref: Instance representing a Data Import reference
  """
  request = client.management().uploads().list(
      accountId=dataimport_ref.account_id,
      webPropertyId=dataimport_ref.property_id,
      customDataSourceId=dataimport_ref.dataset_id)
  response = request.execute()
  if response['items']:
    # Considers an upload as completed when the list of items is not empty.
    return UploadStatus.COMPLETED
  return UploadStatus.PENDING


def delete_oldest_uploads(client: discovery.Resource,
                          dataimport_ref: DataImportReference,
                          max_to_keep: Optional[int] = None) -> list[str]:
  """Deletes the oldest uploads from the referenced Data Import.

  Args:
    client: Google Analytics API client.
    dataimport_ref: References a single Data Import in Google Analytics.
    max_to_keep: The maximum number of uploads to keep, older uploads will be
      deleted. If None, all existing uploads will be deleted. Defaults to None.

  Returns:
    The deleted IDs.

  Raises:
    ValueError: if `max_to_keep` is less than or equal to zero.
  """
  if max_to_keep is not None and max_to_keep <= 0:
    raise ValueError(f'Invalid value for argument `max_to_keep`. '
                     f'Expected a strictly positive value. '
                     f'Received max_to_keep={max_to_keep}.')
  response = client.management().uploads().list(
      accountId=dataimport_ref.account_id,
      webPropertyId=dataimport_ref.property_id,
      customDataSourceId=dataimport_ref.dataset_id).execute()
  sorted_uploads = sorted(response['items'], key=lambda x: x['uploadTime'])
  if max_to_keep is not None:
    uploads_to_delete = sorted_uploads[:-max_to_keep]  # pylint: disable=invalid-unary-operand-type
  else:
    uploads_to_delete = sorted_uploads
  ids_to_delete = [x['id'] for x in uploads_to_delete]
  if ids_to_delete:
    client.management().uploads().deleteUploadData(
        accountId=dataimport_ref.account_id,
        webPropertyId=dataimport_ref.property_id,
        customDataSourceId=dataimport_ref.dataset_id,
        body={'customDataImportUids': ids_to_delete}).execute()
  return ids_to_delete


def upload_dataimport(
    client: discovery.Resource,
    dataimport_ref: DataImportReference,
    filepath: str,
    chunksize: int = 1024 * 1024,
    progress_callback: Optional[Callable[[float], None]] = None) -> None:
  """Uploads the content of a given file to the referenced Data Import.

  Args:
    client: Google Analytics API client.
    dataimport_ref: References a single Data Import in Google Analytics.
    filepath: File path to upload its content to GA.
    chunksize: Integer representing the size of chunks in bytes sent to GA API.
      Defaults value is set to 1MB.
    progress_callback: f(float), The function to call to update the progress
      bar or None for no progress bar.
  """
  media = api_httplib.MediaFileUpload(
      filepath,
      mimetype='application/octet-stream',
      chunksize=chunksize,
      resumable=True)
  request = client.management().uploads().uploadData(
      accountId=dataimport_ref.account_id,
      webPropertyId=dataimport_ref.property_id,
      customDataSourceId=dataimport_ref.dataset_id,
      media_body=media)
  response = None
  while response is None:
    status, response = request.next_chunk(num_retries=_NUMBER_OF_RETRIES)
    if status and progress_callback:
      # Rounds progress up to 4 digits, since we don't need more precision
      # for this percentage.
      progress_callback(round(status.progress(), 4))
  # Sends a completion signal once the upload has finished.
  if progress_callback:
    progress_callback(1.0)


class AudienceOperationBase:
  """Abtract class for operation on audiences."""


Audience = NewType('Audience', dict)
AudiencePatch = NewType('AudiencePatch', dict)
AudienceOperation = TypeVar('AudienceOperation', bound=AudienceOperationBase)


@dataclasses.dataclass(frozen=True)
class AudienceOperationInsert(AudienceOperationBase):
  data: AudiencePatch


@dataclasses.dataclass(frozen=True)
class AudienceOperationUpdate(AudienceOperationBase):
  id: str
  data: AudiencePatch


def fetch_audiences(ga_client: discovery.Resource,
                    account_id: str,
                    property_id: str) -> Mapping[str, Audience]:
  """Returns a mapping of remarketing audiences from Google Analytics API.

  Args:
    ga_client: Google Analytics API client.
    account_id: Identifier for the Google Analytics Account ID.
    property_id: Identifier for the Google Analytics Property to retrieve
      audiences from.
  """
  request = ga_client.management().remarketingAudience().list(
      accountId=account_id,
      webPropertyId=property_id,
      start_index=None,
      max_results=_MAX_RESULTS_PER_CALL)
  result = retry.Retry()(request.execute)()
  items = result['items']
  # If there are more results than could be returned by a single call,
  # continue requesting results until they've all been retrieved.
  while result.get('nextLink', None):
    request.uri = result['nextLink']
    result = retry.Retry()(request.execute)()
    items += result['items']
  return dict((item['name'], Audience(item)) for item in items)


def get_audience_operations(
    patches: list[AudiencePatch],
    audiences_map: Mapping[str, Audience]) -> list[AudienceOperation]:
  """Returns list of operations to insert or update GA remarketing lists.

  Args:
    patches: List of audiences used as update patches.
    audiences_map: Map of audiences to apply patches to.
  """
  operations = []
  for patch in patches:
    target = audiences_map.get(patch['name'], None)
    if target and utils.detect_patch_update(patch, target):
      operations.append(AudienceOperationUpdate(id=target['id'], data=patch))
    else:
      operations.append(AudienceOperationInsert(data=patch))
  return operations


def run_audience_operations(
    ga_client: discovery.Resource,
    account_id: str,
    property_id: str,
    operations: list[AudienceOperation],
    progress_callback: Optional[Callable[[str], None]] = None
) -> None:
  """Executes audience operations.

  Args:
    ga_client: Google Analytics API client.
    account_id: Identifier for the Google Analytics Account ID.
    property_id: Identifier for the Google Analytics Property to update
      remarketing audiences from.
    operations: List of operations on audiences, either insert or update.
    progress_callback: Callback to send progress messages.

  Raises:
    ValueError: if the operation type is unsupported.
  """
  progress_callback = progress_callback or _null_progress_callback
  for op in operations:
    if isinstance(op, AudienceOperationInsert):
      request = ga_client.management().remarketingAudience().insert(
          accountId=account_id,
          webPropertyId=property_id,
          body=op.data)
      progress_callback('Inserting new audience')
    elif isinstance(op, AudienceOperationUpdate):
      request = ga_client.management().remarketingAudience().patch(
          accountId=account_id,
          webPropertyId=property_id,
          remarketingAudienceId=op.id,
          body=op.data)
      progress_callback(f'Updating existing audience for id: {op.id}')
    else:
      raise ValueError(f'Unsupported operation type: {op}')
    retry.Retry()(request.execute)()
