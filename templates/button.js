{% for mod in modules -%}
try { Cu.import('{{ mod }}'); } catch(e) {}
{% endfor %}
{%- if interfaces -%}
{{javascript_object}}.toolbar_button_loader({{javascript_object}}.interfaces, {
	{{ interfaces|join(',\n\t') }}
});
{% endif %}
{%- if functions %}
{{javascript_object}}.toolbar_button_loader({{javascript_object}}, {
	{{ functions|join(',\n\t') }}
});
{% endif %}
{%- if extra %}
window.addEventListener("load", function {{javascript_object}}OnLoad() {
	window.removeEventListener("load", {{javascript_object}}OnLoad, false);
	{{ extra|join('\n\t') }}
	window.sizeToContent();
}, false);
{%- endif %}