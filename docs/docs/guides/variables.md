---
bodyclass: docs
headline: Variables and expressions in CRMint
layout: docs
sidenav: doc-side-guides-nav.html
title: Guides
type: markdown
---

## Variables and expressions in CRMint

CRMint can use dynamically generated parameters throughout a project or pipeline. This allows you to :

*   **Define once, use many times**: A project ID or table name for example, can be used in many places throughout your pipeline(s). Reuse is highly simplified by having this defined in just one place
*   **Adjust to relative changes**: You may want data from a time relative to the time of execution, for example, “4 hours ago”.

### Defining variables

Variables in CRMint can be defined either globally or per-pipeline. Where a variable is defined with the same name both globally *and* in a pipeline, the pipeline version will take precedence.

To add varlables to a pipeline:

1.  In the pipelines view, click on the pipeline, then click **Edit**.
1.  Click **Add variable**, then enter the name by which the variable should be referenced, and the value required.

To add a global variable:

1.  Click on the **Settings** button in the top navigation bar
1.  Click **Add global variable**, and add your variable as per a pipeline

### Using variables

To use your variable simply enclose the variable name in any parameter in your pipeline with `{{` and `}}`

For example, if you have many pipelines, all working with BigQuery, you can set a global variable for the project as follows

    Name: PROJECT_ID
    Value: my-project-123456

In your `BQToMeasurementProtocol` worker, you can then set **Project ID** to:

    {{ PROJECT_ID }}

On execution, the value *my-project-123456* from the global variable is substituted into the worker Project ID.

A more complex example might be setting the comment parameter for a `Commenter` worker:

    Finished execution using project {{ PROJECT_ID }}

This would lead to a log message: *Finished execution using project my-project-123456*

### Evaluation

Not only do the `{{}}` tags enable variables to be substituted into parameters, as shown above, but they also allow evaluation, for example, setting a parameter **Number of Days** to:

    {{ 4 * 7 }}

Would use a value of `28`.

    {{ NUM_WEEKS * 7 }}

Would use the value of variable `NUM_WEEKS` - *assuming it has been defined* - multiplied by 7.

The full detail of what can be achieved using expressions can be seen in the [Jinja2 Expressions syntax guide](https://jinja.palletsprojects.com/en/3.1.x/templates/#expressions).

### Built-in functions

To make evaluation more useful when working with time-based and analytical data, the following built in functions can be used in expressions:

*All examples given at 2018-10-16 12:00:00 UTC*


| ------------------------------------- + -------------------------------------------- + ---------------------------------------------------------------|
|**Built-in function**                  | **Purpose**                                  | **Details**
| :------------------------------------ + :------------------------------------------- + :--------------------------------------------------------------
|**today(format)**                      | Returns today’s date in the specified format | `format` - The desired format, in python date formatting syntax.<br/><br/>Example:<br/><br/>`{{ today("%Y-%m-%d") }}`  *=> 2018-10-16*
| ------------------------------------- + -------------------------------------------- + ---------------------------------------------------------------
|**days_ago(n_days, format)**           | Returns the formatted date for n days ago    | `n_days` - The number of days ago, where yesterday is 1<br/>`format` - The desired format, in [python date formatting syntax](http://strftime.org/).<br/><br/>Example:<br/><br/>`{{ days_ago(1, "%Y-%m-%d") }}` *=> 2018-10-15*
| ------------------------------------- + -------------------------------------------- + ---------------------------------------------------------------
|**hours_ago(n_hours, format)**         | Returns the formatted date for n hours ago   | `n_hours` - The number of hours ago<br/>`format` - The desired format, in [python date formatting syntax](http://strftime.org/).<br/><br/>Example:<br/><br/>`{{ hours_ago(1, "%Y-%m-%d %H:%M:%S") }}` *=> 2018-10-16 11:00:00*
| ------------------------------------- + -------------------------------------------- + ---------------------------------------------------------------
|**days_since(date, format)**           | Returns the number of days since given date  | `date` - A string date<br/>`format` - The format of the date, in [python date formatting syntax](http://strftime.org/).<br/><br/>Example:<br/><br/>`{{ days_since("2018-10-14", "%Y-%m-%d") }}` *=> 2*
| ------------------------------------- + -------------------------------------------- + ---------------------------------------------------------------
|**randint(x)**                         | Returns a random int below x                 |
| ------------------------------------- + -------------------------------------------- + ---------------------------------------------------------------
|**rand()**                             | Returns a random float between 0 and 1       |
