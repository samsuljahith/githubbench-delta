# {{ doc.title }}

**{{ brand.product_name }}** · Generated {{ doc.generated_at }}
{% if doc.experiment_ids %}Experiments: {{ doc.experiment_ids | join(', ') }}{% endif %}

{% for section in sections %}
## {{ section.title }}

{% if section.summary %}{{ section.summary }}

{% endif %}
{% for table in section.tables %}
{% if table.rows %}
{% if table.name %}### {{ table.name }}

{% endif %}
| {% for col in table.columns %}{{ col }} | {% endfor %}
| {% for col in table.columns %}--- | {% endfor %}
{% for row in table.rows %}| {% for col in table.columns %}{{ row.get(col, '') }} | {% endfor %}
{% endfor %}

{% endif %}
{% endfor %}
{% if section.notes %}
{% for note in section.notes %}- {{ note }}
{% endfor %}

{% endif %}
{% for cid in section.chart_ids %}
{% set chart = charts.get(cid) %}
{% if chart %}
### {{ chart.title }}

{% if chart.png_relpath %}![{{ chart.title }}]({{ chart.png_relpath }})
{% else %}_Chart `{{ cid }}` (see HTML/PDF for interactive figure)._
{% endif %}

{% endif %}
{% endfor %}
{% endfor %}
---
{{ footer_text | default(brand.footer_text) }}
