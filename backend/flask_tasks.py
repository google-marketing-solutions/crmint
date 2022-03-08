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


def add(app):
  @app.cli.command()
  def db_seeds():
    """Initialize the database."""
    from controller import database
    database.load_fixtures(logger_func=click.echo)

  @app.cli.command()
  def reset_pipelines():
    """Reset pipelines and jobs statuses."""
    from controller import database
    database.reset_jobs_and_pipelines_statuses_to_idle()
