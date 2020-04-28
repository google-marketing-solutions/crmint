// Copyright 2018 Google Inc
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

import { ElementRef } from '@angular/core';
import { Job } from 'app/models/job';

export class PipelineGraph {
  private node_list = [];
  private maxTotalLevel = 0;

  public collection = [];
  public lines = []; // Lines between nodes

  public boxWidth = 220;
  public boxHeight = 42;
  private hGutter = 20;
  private vGutter = 30;
  public ctxMenuItemHeight = 36;

  // Stage calculated sizes
  public stWidth = 1200;
  public stHeight = 0;

  constructor() {
    // const height = this.element.nativeElement.firstElementChild.getBoundingClientRect().height;
  }

  // Calculate levels for all of jobs
  calculate(jobs: Job[]) {
    // Collection of jobs by levels
    // Used for drawing
    // Example:
    //   {
    //     0 => [job<0,0>, job<1,0>, ..., job<m,0>],
    //     1 => [job<0,1>, job<1,1>, ..., job<m,1>],
    //     ...
    //     n => [job<0,n>, job<1,n>, ..., job<m,n>],
    //   }
    this.collection = [];

    // Set of jobs with children
    // Used for calculation of children
    // Example:
    //   [
    //     {
    //       id: 1,            // - Job ID
    //       job: job<1,1>,    // - Job
    //       children: [],     // - children job ids
    //       parents: [],      // - parent job ids
    //       level: 0,         // - level of job
    //       sublevel: 0,      // - sublevel of job
    //       total_level: 0,   // - total_level of job
    //       x: 0              // - job order on level
    //     },
    //     ...
    //   ]
    this.node_list = [];

    this.lines = [];
    this.maxTotalLevel = 0;

    // FIND OR CREATE NODE
    const find_or_create_node = (job_id, child = null) => {
      let node_item = this.node_list.find(obj => obj.id === job_id);
      if (!node_item) {
        const job = jobs.find(j => j.id === job_id);
        this.node_list.push({
          id: job_id,
          job: job,
          children: [],
          parents: [],
          level: 0,
          sublevel: 0,
          x: 0,
          x_offset: 0,
          y_offset: 0
        });
        node_item = this.node_list[this.node_list.length - 1];
      }
      if (child !== null) {
        node_item.children.push(child.id);
      }
      return node_item;
    };

    // MAPPING JOB AND CHILDREN
    jobs.forEach((job) => {
      const job_node = find_or_create_node(job.id);
      const parent_ids = job.start_conditions.map(obj => obj.preceding_job_id);

      parent_ids.forEach((preceding_job_id) => {
        const sc = jobs.find(obj => obj.id === preceding_job_id);
        if (sc !== undefined) {
          find_or_create_node(preceding_job_id, job);
          job_node.parents.push(preceding_job_id);
        }
      });
    });

    // ADD LEVEL FOR ROOTS
    this.collection[0] = [];

    // ADD CHILDREN

    // ADD LEVEL FOR CHILDREN
    const add_level_for_children = (children_ids, level: number) => {
      if (!children_ids.length) {
        return;
      }
      const children = this.node_list.filter((child) => children_ids.includes(child.id));
      children.forEach((node_item) => {
        if (node_item.level < level) {
          node_item.level = level;
        }
        add_level_for_children(node_item.children, level + 1);
      });
    };

    // ADD LEVELS TO NODE LIST
    this.node_list.forEach((node_item) => {
      if (!node_item.parents.length) {
        add_level_for_children(node_item.children, 1);
      }
    });

    // ADD COLLECTION
    this.node_list.forEach((node_item) => {
      if (!this.collection[node_item.level]) {
        this.collection[node_item.level] = [];
        node_item.x = 0;
      } else {
        node_item.x = this.collection[node_item.level].length;
      }
      this.collection[node_item.level].push(node_item);
    });

    // SORTING
    this.collection.forEach((level_nodes, level) => {
      if (level !== 0) {
        level_nodes.forEach((node) => {
          let x_sum = 0;
          node.job.start_conditions.forEach((start_condition) => {
            const parent = find_or_create_node(start_condition.preceding_job_id);
            x_sum += parent.x;
          });
          node.x = x_sum / node.job.start_conditions.length;
        });
        this.collection[level] = level_nodes.sort((n1, n2) => n1.x - n2.x);
      }
    });

    const getTotalLevel = (_level, _sublevel, index) => {
      if (_level === 0) {
        this.maxTotalLevel = _sublevel;
      } else if (index % 4 === 0) {
        this.maxTotalLevel++;
      }
      return this.maxTotalLevel;
    };

    // Add sublevels and total levels
    this.collection.forEach((level_nodes, level) => {
      level_nodes.forEach((node, i) => {
        node.sublevel = Math.floor(i / 4);
        node.total_level = getTotalLevel(level, node.sublevel, i);
      });
    });

    this.collection.forEach((nodes_on_level, level) => {
      nodes_on_level.forEach((node, i) => this.posCalc(node, i));
    });

    this.stHeight = (this.maxTotalLevel + 1) * (this.boxHeight + this.vGutter) + this.ctxMenuItemHeight * 2 + 5;
  }

  // Add position to node items
  posCalc(node, index) {
    const getXOffset = (_level, _index, _sublevel) => {
      const count_on_level = this.node_list.filter(node_item => node_item.total_level === _level).length;

      const count_gutters_on_level = count_on_level - 1;
      const x_center = this.stWidth / 2;
      const x0_on_level = x_center - (this.boxWidth * count_on_level + this.hGutter * count_gutters_on_level) / 2;
      return x0_on_level + (this.boxWidth + this.hGutter) * (_index - _sublevel * 4);
    };
    const getYOffset = (_total_level, _sublevel, _level) => {
      return this.vGutter + _total_level * this.boxHeight
                          + (_total_level - _level) * this.vGutter / 3
                          + _level * this.vGutter;
    };
    node.x_offset = getXOffset(node.total_level, index, node.sublevel);
    node.y_offset = getYOffset(node.total_level, node.sublevel, node.level);

    this.linesCalc(node, node.x_offset, node.y_offset);
  }

  // Calculate points for Lines
  linesCalc(node, x_offset, y_offset) {
    // connection with parents
    const point1 = {
      x: x_offset + this.boxWidth / 2,
      y: y_offset
    };

    node.job.start_conditions.forEach((start_condition) => {
      const parent_job_id = start_condition.preceding_job_id;
      const parent_node = this.node_list.find(obj => obj.id === parent_job_id);
      if (!parent_node) {
        return;
      }
      const i = this.collection[parent_node.level].map(obj => obj.id).indexOf(parent_job_id);
      const point2 = {
        x: parent_node.x_offset + this.boxWidth / 2,
        y: parent_node.y_offset + this.boxHeight
      };
      this.lines.push({
        id: node.job.id,
        points: [
          point1.x, point1.y,
          point2.x, point2.y
        ]
      });
    });
  }

}
