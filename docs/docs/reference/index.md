---
bodyclass: docs
headline: CRMint workers reference
layout: docs
sidenav: doc-side-reference-nav.html
type: markdown
---


Pipelines can be imported and exported in JSON format. This reference provides detail of the JSON document structure.

### Pipeline

Defines a CRMint pipeline. This is the root object of a document for import.

<table>
  <tr>
   <th><strong>Property</strong>
   </th>
   <th><strong>Type</strong>
   </th>
   <th><strong>Required</strong>
   </th>
   <th><strong>Description</strong>
   </th>
  </tr>
  <tr>
   <td>name
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The name of the pipeline.
   </td>
  </tr>
  <tr>
   <td>jobs
   </td>
   <td>
    <a href="#job">Job</a>[]
   </td>
   <td>False
   </td>
   <td>A list of Job nodes which make up the execution graph of the pipeline.
   </td>
  </tr>
  <tr>
   <td>params
   </td>
   <td>
    <a href="#variable">Variable</a>[]
   </td>
   <td>True
   </td>
   <td>A list of pipeline-level variables.
   </td>
  </tr>
  <tr>
   <td>run_on_schedule
   </td>
   <td>boolean
   </td>
   <td>False
   </td>
   <td>Whether the pipeline is scheduled
   </td>
  </tr>
  <tr>
   <td>schedules
   </td>
   <td>
    <a href="#schedule">Schedule</a>[]
   </td>
   <td>True
   </td>
   <td>A list of Schedule definitions, for automated pipeline execution.
   </td>
  </tr>
  <tr>
   <td>emails_for_notifications
   </td>
   <td>string
   </td>
   <td>False
   </td>
   <td>A whitespace-delimited string of email addresses
   </td>
  </tr>
</table>


### Job

Defines a single worker node in the execution graph.


<table>
  <tr>
   <th><strong>Property</strong>
   </th>
   <th><strong>Type</strong>
   </th>
   <th><strong>Required</strong>
   </th>
   <th><strong>Description</strong>
   </th>
  </tr>
  <tr>
   <td>id
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>An ID to uniquely identify this node in the execution graph, such as a UUID.
   </td>
  </tr>
  <tr>
   <td>name
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>A name to describe the purpose of this Job node.
   </td>
  </tr>
  <tr>
   <td>worker_class
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The node type for this job, for example: <code>BQQueryLauncher</code>
    <br/><br/>
    See <a href="worker_spec.html">Worker specification</a>
   </td>
  </tr>
  <tr>
   <td>params
   </td>
   <td>
    <a href="#param">Param</a>[]
   </td>
   <td>True
   </td>
   <td>A list of job-level parameters.
   </td>
  </tr>
  <tr>
   <td>hash_start_conditions
   </td>
   <td>
    <a href="#startcondition">StartCondition</a>[]
   </td>
   <td>True
   </td>
   <td>A list of conditions for the job node to start execution, for example, successful execution of previous jobs in the graph. All must evaluate to true.
   </td>
  </tr>
</table>



### Variable

Defines a pipeline-level variable


<table>
  <tr>
   <th><strong>Property</strong>
   </th>
   <th><strong>Type</strong>
   </th>
   <th><strong>Required</strong>
   </th>
   <th><strong>Description</strong>
   </th>
  </tr>
  <tr>
   <td>name
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The variable name.
   </td>
  </tr>
  <tr>
   <td>type
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The type. This should be set to <code>text</code>
   </td>
  </tr>
  <tr>
   <td>value
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The variable value.
   </td>
  </tr>
</table>



### Schedule

Defines a frequency for automated execution


<table>
  <tr>
   <th><strong>Property</strong>
   </th>
   <th><strong>Type</strong>
   </th>
   <th><strong>Required</strong>
   </th>
   <th><strong>Description</strong>
   </th>
  </tr>
  <tr>
   <td>cron
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The <a href="https://crontab.guru/">cron specification</a>
   </td>
  </tr>
</table>



### Param

A setting used as an input to a [Job](#job) node.


<table>
  <tr>
   <th><strong>Property</strong>
   </th>
   <th><strong>Type</strong>
   </th>
   <th><strong>Required</strong>
   </th>
   <th><strong>Description</strong>
   </th>
  </tr>
  <tr>
   <td>name
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The variable name.
   </td>
  </tr>
  <tr>
   <td>type
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The type. Valid options include:<ul>

<li><code>string</code></li>
<li><code>sql</code></li>
<li><code>number</code></li>
<li><code>boolean</code></li></ul>

   </td>
  </tr>
  <tr>
   <td>value
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The variable value.
   </td>
  </tr>
  <tr>
   <td>description
   </td>
   <td>string
   </td>
   <td>False
   </td>
   <td>?
   </td>
  </tr>
  <tr>
   <td>label
   </td>
   <td>string
   </td>
   <td>False
   </td>
   <td>?
   </td>
  </tr>
  <tr>
   <td>is_required
   </td>
   <td>boolean
   </td>
   <td>False
   </td>
   <td>Whether the parameter is mandatory: Defaults to <code>false</code>.
   </td>
  </tr>
</table>



### StartCondition

Used to define the conditions under which a [Job](#job) will start


<table>
  <tr>
   <th><strong>Property</strong>
   </th>
   <th><strong>Type</strong>
   </th>
   <th><strong>Required</strong>
   </th>
   <th><strong>Description</strong>
   </th>
  </tr>
  <tr>
   <td>preceding_job_id
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>The ID of the job on which this condition depends
   </td>
  </tr>
  <tr>
   <td>condition
   </td>
   <td>string
   </td>
   <td>True
   </td>
   <td>Possible values are:<ul>

<li><code>success</code></li>
<li><code>fail</code></li>
<li><code>whatever</code> - implies outcome is not important but the job referred to by <code>preceding_job_id</code> must have executed.</li></ul>

   </td>
  </tr>
</table>


