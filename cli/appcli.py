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

PLUGIN_FOLDER = os.path.join(os.path.dirname(__file__), 'commands')

class CRMintCLI(click.MultiCommand):
  """App multi command CLI"""
  def list_commands(self, ctx):
      rv = []
      for filename in os.listdir(PLUGIN_FOLDER):
          if not filename.startswith("_"):
              rv.append(filename[:-3])
      rv.sort()
      print(rv)
      return rv

  def get_command(self, ctx, name):
      ns = {}
      fn = os.path.join(PLUGIN_FOLDER, "%s%s" % (name, ".py"))
      with open(fn) as f:
          code = compile(f.read(), fn, 'exec')
          eval(code, ns, ns)
      return ns['cli']

CLI = CRMintCLI(help='CRMint commands:')

def entry_point():
  CLI()

if __name__ == '__main__':
  CLI()
