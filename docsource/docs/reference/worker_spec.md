---
bodyclass: docs
headline: CRMint workers reference
layout: docs
type: markdown
---

Workers are the fundamental building blocks used in creating your CRMint
pipeline - see [CRMint concepts](../guides/concepts.html) for more details.

The following is the list of available workers, with their configuration
options.

{% for worker in page.workers %}
<div>
<h1>{{ worker.name | textualize }}</h1>
<h3>{{ worker.description | textualize }}</h3>

{% if worker.detail.size > 1 %}
<p>
{{ worker.detail | newline_to_br }}
</p>
{% endif %}

{% if worker.parameters %}
  <strong>Parameters</strong>
  <table>
    <tr><th>Parameter name</th><th>Data type</th><th>Required</th><th>Default value</th><th>Description</th></tr>
    {% for row in worker.parameters %}
    <tr><td>{{ row[0] }}</td><td>{{ row[1] }}</td><td>{{ row[2] }}</td><td>{{ row[3] }}</td><td>{{ row[4] }}</td></tr>
    {% endfor %}
  </table>
{% else %}
<p>The worker does not take parameters</p>
{% endif %}
</div>
{% endfor %}
