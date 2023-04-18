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

import click
from flask.app import Flask

from controller import database


def add(app: Flask) -> None:
  """Adds tasks to the Flask app."""

  @app.cli.command()
  def db_seeds():
    """Initialize the database."""
    database.load_fixtures(logger_func=click.echo)
