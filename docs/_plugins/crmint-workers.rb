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

module Workers
  class Generator < Jekyll::Generator
    WORKER_PATH = "../backends/core/workers.py"

    def generate(site)
      workers = get_worker_details()

      worker_page = site.pages.detect {|page| page.name == 'worker_spec.md'}
      worker_page.data['workers'] = workers
    end

    def get_worker_details()
      pycode = get_file_as_string(WORKER_PATH)

      available = Set[]
      workers = []
      worker_name = nil
      worker_description = nil
      worker_detail = ""
      in_param = false
      in_available = false
      in_detail = false
      params = ''

      pycode.each { |line|
        matches = /^\s*class\s+([^(\n]+).*:$/.match(line)
        if matches
          if worker_name && worker_description.length > 0
            worker = {
              "name" => worker_name,
              "description" => worker_description,
              "detail" => worker_detail
            }
            if params.length > 0
              worker["parameters"] = parse_params(params)
            end
            if available.include?(worker_name)
              workers.push(worker)
            end
            worker_name = nil
            worker_description = nil
            worker_detail = ""
            params = ''
          end
          worker_name = matches[1]
        elsif worker_name
          if !worker_description && !in_detail
            matches = /^\s*\"\"\"(.*)\"\"\"\s*$/.match(line)
            if matches
              worker_description = matches[1]
            else
              matches = /^\s*\"\"\"(.*)$/.match(line)
              if matches
                in_detail = true
                worker_description = matches[1].lstrip
              end
            end
          elsif in_detail
            matches = /^(.*)\"\"\"\s*$/.match(line)
            if matches
              in_detail = false
              worker_detail += matches[1].lstrip
            elsif line.strip.length == 0 && worker_detail.length > 0
              worker_detail += "\n"
            else
              worker_detail += line.lstrip
            end
          elsif worker_description && !in_param
            matches = /^\s*PARAMS\s=\s(.*)/.match(line)
            if matches
              in_param = true
              params += matches[1]
            end
          elsif in_param
            matches = /^\s*$/.match(line)
            if matches
              in_param = false
            else
              params += line
            end
          end
        elsif in_available
          matches = /^\s*\)\s*$/.match(line)
          if matches
            in_available = false
          else
            matches = /^\s*'(.*)',\s*$/.match(line)
            if matches
              available.add(matches[1])
            end
          end
        else
          if line =~ /^\s*AVAILABLE\s*=\s*.*/
            in_available = true
          end
        end
      }

      if worker_name && worker_description.length > 0
        worker = {
          "name" => worker_name,
          "description" => worker_description,
          "detail" => worker_detail
        }
        if params.length > 0
          worker["parameters"] = parse_params(params)
        end
        workers.push(worker)
      end
      return workers.sort_by { |h| h["name"] }
    end

    def parse_params(params)
      x = []
      r = params.gsub(/\n\s*/, '')
      r = r.gsub(/^\[\s+\(/, '')
      r = r.gsub(/\)\s*,\s*\]\s*$/, '')
      p = r.split("),(")
      if p.length > 0
        p.each { |c|
          rows = CSV.parse(c, {:quote_char => "\01", :converters => [
            -> field, info {
                field = field.strip
                if /^'(.*)'$/.match(field)
                  field[1..-2]
                elsif /^\('(.*)'\)$/.match(field)
                  field = field[2..-4]
                  field.gsub(/''/, "")
                else
                  field
                end
            }
          ]})
          x.push(rows[0])
        }
      end
      return x
    end

    def get_file_as_string(filename)
      return File.readlines(filename)
    end
  end
end
