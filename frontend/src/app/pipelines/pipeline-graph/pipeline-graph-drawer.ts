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

import Konva from 'konva';
import { PipelineGraph } from './pipeline-graph';
import { Job } from 'app/models/job';

export class PipelineGraphDrawer {
  private pgraph: PipelineGraph;
  private stage: Konva.Stage;
  private jobs: Job[];

  private ctxMenuZone = { x: [], y: [] };
  private ctxMenuShown = null;

  // Colors
  private lineColor = '#CFD8DC';
  private highlightColor = '#21cccb';
  private borderColor = '#CFD8DC';
  private textColor = '#212121';
  private blockedTextColor = '#9E9E9E';

  // Tooltip
  private tooltip = new Konva.Text({
    text: '',
    fontFamily: 'Roboto',
    fontSize: 12,
    padding: 5,
    fill: 'white',
  });
  private btooltip = new Konva.Tag({
    fill: 'black',
    pointerDirection: 'down',
    pointerWidth: 10,
    pointerHeight: 5,
    lineJoin: 'round',
    shadowColor: 'black',
    shadowBlur: 10,
    shadowOpacity: 0.5
  });
  private gtooltip = new Konva.Label({
    opacity: 0.75,
    visible: false
  });

  // Context menu
  private gctxmenu = new Konva.Group({});
  private bctxmenu = new Konva.Rect({
    width: 120,
    height: 70,
    fill: 'white',
    strokeWidth: 1,
    stroke: this.borderColor,
    shadowColor: this.borderColor,
    shadowBlur: 3,
    shadowOffset: {x : 1, y : 2},
    shadowOpacity: 0.5
  });

  // LAYERS
  private layerJobBoxes;
  private layerLines;
  private layerTooltip;
  private layerContextMenu;

  // STATUS ICON
  private svgStatuses = {
    idle: {
      // tslint:disable-next-line
      data: 'M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z',
      fill: this.textColor
    },
    waiting: {
      // tslint:disable-next-line
      data: 'M13,16V8H15V16H13M9,16V8H11V16H9M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22A10,10 0 0,1 2,12A10,10 0 0,1 12,2M12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4Z',
      fill: '#FFB74D'
    },
    running: {
      // tslint:disable-next-line
      data: 'M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M10,16.5L16,12L10,7.5V16.5Z',
      fill: '#42A5F5'
    },
    stopping: {
      // tslint:disable-next-line
      data: 'M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4M9,9V15H15V9',
      fill: '#EF5350'
    },
    failed: {
      // tslint:disable-next-line
      data: 'M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2C6.47,2 2,6.47 2,12C2,17.53 6.47,22 12,22C17.53,22 22,17.53 22,12C22,6.47 17.53,2 12,2M14.59,8L12,10.59L9.41,8L8,9.41L10.59,12L8,14.59L9.41,16L12,13.41L14.59,16L16,14.59L13.41,12L16,9.41L14.59,8Z',
      fill: '#E57373'
    },
    succeeded: {
      // tslint:disable-next-line
      data: 'M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22A10,10 0 0,1 2,12A10,10 0 0,1 12,2M12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4M11,16.5L6.5,12L7.91,10.59L11,13.67L16.59,8.09L18,9.5L11,16.5Z',
      fill: '#4CAF50'
    }
  };

  constructor(
    private context, // PipelineGraphComponent
  ) {
    this.context = context;
    this.jobs = context.jobs;
    this.pgraph = new PipelineGraph(context.element);
  }

  private calculate() {
    this.pgraph.calculate(this.jobs);
  }

  public redraw() {
    if (this.stage) {
      this.destroy();
    }
    this.jobs = this.context.jobs;
    this.calculate();
    this.drawStage();
  }

  public drawStage() {
    this.ctxMenuZone = {x: [], y: []};

    this.stage = new Konva.Stage({
      container: 'crmi-pipeline-graph',
      width: this.pgraph.stWidth,
      height: this.pgraph.stHeight
    });

    this.layerLines = new Konva.Layer();
    this.stage.add(this.layerLines);

    // Job box layer
    this.layerJobBoxes = new Konva.Layer();
    this.stage.add(this.layerJobBoxes);

    // Add layer Tooltip
    this.layerTooltip = new Konva.Layer();
    this.gtooltip.add(this.btooltip);
    this.gtooltip.add(this.tooltip);
    this.layerTooltip.add(this.gtooltip);
    this.stage.add(this.layerTooltip);

    // Context Menu Layer
    this.layerContextMenu = new Konva.Layer();
    this.stage.add(this.layerContextMenu);

    // Draw Layers
    this.drawLines();
    this.drawJobBoxes();

    this.layerLines.on('click', (event) => {
      if (this.ctxMenuShown) {
        const [x, y] = [
          this.stage.getPointerPosition().x,
          this.stage.getPointerPosition().y
        ];
        let inZone = false;
        this.ctxMenuZone.x.forEach((xRange, i) => {
          const yRange = this.ctxMenuZone.y[i];
          if (x >= xRange[0] && x <= xRange[1] && y >= yRange[0] && y <= yRange[1]) {
            inZone = true;
          }
        });

        if (!inZone) {
          this.ctxMenuShown = null;
          this.drawContextMenu();
        }
      }
    });
  }

  drawJobBoxes() {
    this.layerJobBoxes.removeChildren();
    // Draw jobs
    this.pgraph.collection.forEach((nodes_on_level, level) => {
      nodes_on_level.forEach((node) => {
        this.drawJobBox(node);
      });
    });

    this.layerJobBoxes.draw();
  }

  redrawJobBox(node, hovered = false) {
    const jobBox = this.layerJobBoxes.find(`#jobBox${node.job.id}`);
    jobBox.remove();
    const group = this.drawJobBox(node, hovered);
    group.draw();
  }

  drawJobBox(node, hovered = false) {
    const group = new Konva.Group({
      x: node.x_offset,
      y: node.y_offset,
      id: `jobBox${node.job.id}`
    });

    const statusIcon = new Konva.Path({
      x: 10,
      y: 10,
      scaleX: 0.9,
      scaleY: 0.9,
      data: this.svgStatuses[node.job.status].data,
      fill: this.svgStatuses[node.job.status].fill
    });
    // END STATUS ICON

    const jobText = this.fittingString(this.layerJobBoxes.getContext(), node.job.name, this.pgraph.boxWidth - 120);

    const jobNameText = new Konva.Text({
      x: 29,
      y: 4,
      text: jobText,
      fontSize: 15,
      fontFamily: 'Roboto',
      padding: 10,
      fill: hovered ? this.highlightColor : this.textColor,
      fontStyle: 'normal'
    });

    node.showToolTip = jobText.indexOf('…') > -1;

    // create shape
    const box = new Konva.Rect({
        x: 0,
        y: 0,
        width: this.pgraph.boxWidth,
        height: this.pgraph.boxHeight,
        fill: 'white',
        stroke: hovered ? this.highlightColor : this.borderColor,
        strokeWidth: 1,
        cornerRadius: 5
    });

    // DOTS BTN GROUP
    const dotsVertIcon = new Konva.Path({
      x: 0,
      y: 8,
      scaleX: 0.8,
      scaleY: 0.8,
      // tslint:disable-next-line
      data: 'M12,16A2,2 0 0,1 14,18A2,2 0 0,1 12,20A2,2 0 0,1 10,18A2,2 0 0,1 12,16M12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12A2,2 0 0,1 12,10M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4Z',
      fill: this.textColor
    });

    const dotsBtnGroup = new Konva.Group({
      x: this.pgraph.boxWidth - 30,
      y: 4,
    });
    const dotsArea = new Konva.Rect({
      x: 0,
      y: 0,
      width: 23,
      height: 32,
      fill: 'transparent'
    });
    dotsBtnGroup.add(dotsArea);
    dotsBtnGroup.add(dotsVertIcon);
    this.ctxMenuZone.x.push([
      node.x_offset + this.pgraph.boxWidth - 30,
      node.x_offset + this.pgraph.boxWidth - 30 + 23,
    ]);
    this.ctxMenuZone.y.push([
      node.y_offset + 4,
      node.y_offset + 4 + 32
    ]);

    box.on('mouseover', () => {
      document.body.style.cursor = 'pointer';
      this.redrawJobBox(node, true);
    });
    jobNameText.on('mouseover', () => {
      document.body.style.cursor = 'pointer';
      this.redrawJobBox(node, true);
    });
    box.on('mouseout', () => {
      document.body.style.cursor = null;
      this.redrawJobBox(node, false);
    });
    jobNameText.on('mouseout', () => {
      document.body.style.cursor = null;
      this.redrawJobBox(node, false);
    });
    box.on('click', () => {
      this.context.onJobEdit(node.job);
    });
    jobNameText.on('click', () => {
      this.context.onJobEdit(node.job);
    });

    // DOTS EVENTS
    dotsBtnGroup.on('mouseover', () => {
        document.body.style.cursor = 'pointer';
    });
    dotsBtnGroup.on('mouseout', () => {
        document.body.style.cursor = null;
    });
    dotsBtnGroup.on('click', () => {
      if (this.ctxMenuShown === null || this.ctxMenuShown.job_id !== node.job.id) {
        this.ctxMenuShown = {
          job_id: node.job.id,
          position: box.getAbsolutePosition(),
          size: {
            width: this.pgraph.boxWidth,
            height: this.pgraph.boxHeight
          }
        };
      } else {
        this.ctxMenuShown = null;
      }
      this.drawContextMenu();
    });
    // END DOTS BTN GROUP

    group.on('mouseover', (e) => {
      if (node.showToolTip) {
        this.drawTooltip(node, true);
      }
      const lines = this.pgraph.lines.filter(l => l.id === node.job.id);
      if (lines.length) {
        lines.forEach(line => line.color = this.highlightColor);
        this.drawLines();
      }
    });

    group.on('mouseout', (e) => {
      if (node.showToolTip) {
        this.drawTooltip(node, false);
      }
      const lines = this.pgraph.lines.filter(l => l.id === node.job.id);
      if (lines.length) {
        lines.forEach(line => line.color = this.lineColor);
        this.drawLines();
      }
    });

    group.add(box);
    group.add(jobNameText);
    group.add(statusIcon);
    group.add(dotsBtnGroup);
    this.layerJobBoxes.add(group);
    return group;
  }

  drawTooltip(node, show) {
    if (show) {
      this.gtooltip.position({
        x: node.x_offset + this.pgraph.boxWidth / 2,
        y: node.y_offset + 10,
      });
      this.tooltip.text(node.job.name);
      this.gtooltip.show();
      this.layerTooltip.batchDraw();
    } else {
      this.gtooltip.hide();
      this.layerTooltip.draw();
    }
  }

  drawLines() {
    this.layerLines.removeChildren();
    const bg = new Konva.Rect({
      x: 0,
      y: 0,
      width: this.pgraph.stWidth,
      height: this.pgraph.stHeight
    });
    this.layerLines.add(bg);

    this.pgraph.lines.forEach((nLine) => {
      const line = new Konva.Line({
        x: 0,
        y: 0,
        points: nLine.points,
        stroke: nLine.color || this.lineColor,
        tension: 1
      });
      this.layerLines.add(line);
    });
    this.layerLines.draw();
  }

  drawContextMenu() {
    this.layerContextMenu.removeChildren();
    if (this.ctxMenuShown === null) {
      this.layerContextMenu.draw();
      return;
    }
    const job = this.jobs.find(obj => obj.id === this.ctxMenuShown.job_id);
    this.gctxmenu.position({
      x: this.ctxMenuShown.position.x + this.ctxMenuShown.size.width - 30,
      y: this.ctxMenuShown.position.y + this.ctxMenuShown.size.height - 35
    });
    this.gctxmenu.add(this.bctxmenu);

    const menuItems = [
      {
        action: 'edit',
        text: 'Edit',
        // tslint:disable-next-line
        data: 'M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z'
      },
      {
        action: 'remove',
        text: 'Remove',
        data: 'M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z'
      },
      {
        action: 'start',
        text: 'Start',
        data: 'M8,5.14V19.14L19,12.14L8,5.14Z'
      }
    ];

    menuItems.forEach((menuItem, i) => {
      const itemGroup = new Konva.Group({
        x: 0,
        y: i * this.pgraph.ctxMenuItemHeight
      });
      const item = new Konva.Text({
        x: 23,
        y: 1,
        text: menuItem.text,
        fontFamily: 'Roboto',
        fill: this.context.pipeline.blocked_managing() ? this.blockedTextColor : this.textColor,
        fontSize: 15,
        padding: 10
      });
      const icon = new Konva.Path({
        x: 7,
        y: 8,
        scaleX: 0.8,
        scaleY: 0.8,
        data: menuItem.data,
        fill: this.context.pipeline.blocked_managing() ? this.blockedTextColor : this.textColor,
      });
      const bg = new Konva.Rect({
        x: 0,
        y: 0,
        width: 120,
        height: this.pgraph.ctxMenuItemHeight,
        fill: 'white',
        stroke: this.borderColor,
        strokeWidth: 1
      });
      itemGroup.add(bg);
      itemGroup.add(item);
      itemGroup.add(icon);

      if (!this.context.pipeline.blocked_managing()) {
        itemGroup.on('mouseover', () => {
          document.body.style.cursor = 'pointer';
        });
        itemGroup.on('mouseout', () => {
          document.body.style.cursor = null;
        });
        itemGroup.on('click', () => {
          switch (menuItem.action) {
            case 'start':
              this.context.onJobStart(job);
              break;
            case 'edit':
              this.context.onJobEdit(job);
              break;
            case 'remove':
              this.context.onJobRemove(job);
              break;
          }
          this.ctxMenuShown = null;
          this.drawContextMenu();
          document.body.style.cursor = null;
        });
      }
      this.gctxmenu.add(itemGroup);
    });

    this.layerContextMenu.add(this.gctxmenu);
    this.layerContextMenu.draw();
  }

  public clickOutside() {
    if (this.ctxMenuShown !== null) {
      this.ctxMenuShown = null;
      this.drawContextMenu();
    }
  }

  public destroy() {
    this.stage.destroy();
  }

  fittingString(c, str, maxWidth) {
    let width = c.measureText(str).width;
    const ellipsis = '…';
    const ellipsisWidth = c.measureText(ellipsis).width;
    if (width <= maxWidth || width <= ellipsisWidth) {
      return str;
    } else {
      let len = str.length;
      while (width >= maxWidth - ellipsisWidth && len-- > 0) {
        str = str.substring(0, len);
        width = c.measureText(str).width;
      }
      return str + ellipsis;
    }
  }
}
