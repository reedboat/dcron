{% extends "_layout/application.tpl" %}
{% block title %} 修改任务 {%endblock%}

{% block styles %}
	<link type="text/css" href="/static/css/lib/jquery-ui-1.10.3.custom.css" rel="stylesheet" />
	<link type="text/css" href="/static/css/lib/jquery-ui-timepicker-addon.css" rel="stylesheet" />
{%endblock%}
{% block scripts%}
	<script type="text/javascript" src="/static/js/lib/jquery-ui-1.10.3.custom.js"></script>
	<script type="text/javascript" src="/static/js/lib/jquery.ui.datepicker.js"></script>
	<script type="text/javascript" src="/static/js/lib/jquery.ui.slider.js"></script>
	<script type="text/javascript" src="/static/js/lib/jquery-ui-timepicker-addon.js"></script>
	<script type="text/javascript" src="/static/js/lib/jquery-ui-timepicker-zh-CN.js"></script>
	<script type="text/javascript" src="/static/js/task_edit.js"></script>
{% endblock %}
{% block content %}
<h2>编辑任务</h2>
{% load crispy_forms_tags %}
{% crispy form %}
{% endblock %}
