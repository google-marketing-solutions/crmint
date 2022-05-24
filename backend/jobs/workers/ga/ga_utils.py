"""Utilities for Google Analytics workers."""

import dataclasses
import enum
import functools
from typing import Optional, Union

from googleapiclient import discovery
from googleapiclient import http as api_httplib
import httplib2


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
