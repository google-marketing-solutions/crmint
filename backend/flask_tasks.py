# Copyright 2018 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

import click

from controller import database
from controller import models


def add(app):
  @app.cli.command()
  def db_seeds():
    """Initialize the database."""
    database.load_fixtures(logger_func=click.echo)

  @app.cli.command()
  def reset_pipelines():
    """Reset pipelines and jobs statuses."""
    database.reset_jobs_and_pipelines_statuses_to_idle()

  @app.cli.command()
  @click.argument('files', nargs=-1)
  def import_pipelines(files):
    for filename in files:
      with open(filename) as f:
        data = json.loads(f.read())
        pipeline = models.Pipeline(name=data['name'])
        pipeline.save()
        pipeline.import_data(data)
