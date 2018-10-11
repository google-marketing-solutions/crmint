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

import os
import click


PLUGIN_FOLDER = os.path.join(os.path.dirname(__file__), 'crmint_commands')


class CRMintCLI(click.MultiCommand):
  """App multi command CLI"""

  def __init__(self, *args, **kwargs):
    click.MultiCommand.__init__(self, *args, **kwargs)

  def list_commands(self, ctx):
    rv = []
    for filename in os.listdir(PLUGIN_FOLDER):
      if not filename.startswith("_") and filename.endswith(".py"):
        rv.append(filename[:-3])
    rv.sort()
    return rv

  def get_command(self, ctx, name):
    ns = {}
    full_name = os.path.join(PLUGIN_FOLDER, "%s%s" % (name, ".py"))
    with open(full_name) as f:
      code = compile(f.read(), full_name, 'exec')
      eval(code, ns, ns)
    return ns['cli']


CLI = CRMintCLI(help='CRMint commands:')


def check_variables():
  if not os.environ["GOOGLE_CLOUD_SDK"]:
    print "not env"
    import subprocess
    gcloud_path = subprocess.Popen("gcloud --format='value(installation.sdk_root)' info",
                                   shell=True, stdout=subprocess.PIPE)
    os.environ["GOOGLE_CLOUD_SDK"] = gcloud_path.communicate()[0]
  # Cloud sql proxy
  cloud_sql_proxy_path = "/usr/bin/cloud_sql_proxy"
  home_path = os.environ["HOME"]
  if os.path.isfile(cloud_sql_proxy_path):
    os.environ["CLOUD_SQL_PROXY"] = cloud_sql_proxy_path
  else:
    cloud_sql_proxy = "{}/bin/cloud_sql_proxy".format(home_path)
    if not os.path.isfile(cloud_sql_proxy):
      click.echo("\rDownloading cloud_sql_proxy to ~/bin/", nl=False)
      os.mkdir("{}/bin".format(home_path), 0755)
      cloud_sql_download_link = "https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64"
      download_command = "curl -L {} -o {}".format(cloud_sql_download_link,
                                                   os.environ["CLOUD_SQL_PROXY"])
      download_status = subprocess.Popen(download_command,
                                         shell=True,
                                         stdout=subprocess.PIPE).communicate()[0]
      if download_status != 0:
        click.echo("[w]Could not download cloud sql proxy")


def entry_point():
  check_variables()
  CLI()
