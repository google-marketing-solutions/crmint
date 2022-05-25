"""Utilities for Google Analytics workers."""

import dataclasses
import enum
import functools
import re
from typing import Callable, Optional, Union

from googleapiclient import discovery
from googleapiclient import http as api_httplib
import httplib2

_NUMBER_OF_RETRIES = 3


@functools.cache
def get_client(
    version: str = 'v4',
    http: Optional[Union[httplib2.Http, api_httplib.HttpMock]] = None,
    request_builder: Optional[Union[api_httplib.HttpRequest,
                                    api_httplib.RequestMockBuilder]] = None
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


def extract_accountid(property_id: str) -> str:
  """Returns the account id part from a Google Analytics property id.

  Args:
    property_id: String containing the property id. Valid formats are
      "GA-XXXXXX-Y" or "UA-XXXXXX-Y".

  Raises:
    ValueError: if the given property id has an invalid format.
  """
  match = re.fullmatch(r'(?:UA|GA)-(\d+)-\d+', property_id)
  if not match:
    raise ValueError(f'Invalid Property ID. Expected format should be either '
                     f'"UA-XXXXXX-Y" or "GA-XXXXXX-Y", but got "{property_id}"')
  return match.group(1)


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
