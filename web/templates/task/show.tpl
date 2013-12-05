{% extends "_layout/application.tpl" %}
{% load datetype %}
{% block title %} 查看任务 {%endblock%}

{%block styles %}
<style>
	ul{list-style:none;}
</style>
{%endblock%}

{% block content %}
<div style="margin-left:auto;margin-right:auto;text-align:center;" id="middle">
	<h1>{{current_task.name}}</h1>
	<div style="padding-bottom:5px;padding-left:10px;">
		创建人：{{current_task.create_by}}&nbsp&nbsp&nbsp&nbsp创建时间：{{current_task.create_at}}
	</div>
	<hr>
	<div style="width:500px;margin-left:auto;margin-right:auto;text-align:center;">
		<div style="text-align:left;" >
			<h3>任务描述</h3>
			<p>
			<ul>
				{% if current_task.discription == "" %}
				无
				{% else %}
					{{current_task.discription}}
				{% endif %}	
			</ul>
			</p>
		</div>
		
		<hr size=3 color='black'>
		<div style="text-align:left;">
			<h3>请求详情</h3>
			<ul class="list">
				<li>
					<p>
						<b>请求URL</b>
						--&nbsp&nbsp&nbsp{{current_task.run_entry}}
					</p>
					<p>
						<b>请求方式</b>
						--&nbsp&nbsp&nbsp{{current_task.run_type}}
					</p>
					<p>
						<b>请求主机</b>
						--&nbsp&nbsp&nbsp{{current_task.run_host}}
					</p>
					<p>
						<b>请求参数</b>
						--&nbsp&nbsp&nbsp{{current_task.run_params}}
					</p>
				</li>
				<li>
				</li>
			</ul>
		</div>
		
		<hr size=3 color='black'>
		
		<div style="text-align:left;" >
			<h3>运行时间</h3>
			<p>
			<ul>
				{% if current_task.type == "date" %}
				在{{current_task.run_time}}时候运行
				{% elif current_task.type == "interval" %}
				每间隔{{current_task.run_time|transdate}}运行
				{% elif current_task.type == "cron" %}
				CRON&nbsp{{current_task.run_time}}
				{% endif %}
			</ul>
			</p>
			<p>
			<ul>
				<b>状态：</b>
				{% if current_task.status == "finished" %}
				已结束
				{% elif current_task.status == "normal" %}
				正常
				{% elif current_task.status == "disabled" %}
				过期
				{% endif %}
			</ul>
			</p>
		</div>
		
		<hr size=3 color='black'>
		<div style="text-align:left;" >
			<h3>运行状态</h3>
			<ul class="list">
				<li>
					<p>
						<b>运行总次数</b>
						--&nbsp&nbsp&nbsp{{current_task.stats.total}}
					</p>
					<p>
						<b>成功次数</b>
						&nbsp&nbsp&nbsp&nbsp--&nbsp&nbsp&nbsp{{current_task.stats.success}}
						<b>&nbsp&nbsp&nbsp&nbsp成功率&nbsp</b>
						&nbsp&nbsp&nbsp&nbsp--&nbsp&nbsp&nbsp{{current_task.stats.success_rate}}
					</p>
					<p>
						<b>失败次数</b>
						&nbsp&nbsp&nbsp&nbsp--&nbsp&nbsp&nbsp{{current_task.stats.failed}}
						<b>&nbsp&nbsp&nbsp&nbsp失败率&nbsp</b>
						&nbsp&nbsp&nbsp&nbsp--&nbsp&nbsp&nbsp{{current_task.stats.failed_rate}}
					</p>
					<p>
						<b>missed</b>
						&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp--&nbsp&nbsp{{current_task.stats.missed}}
						<b>&nbsp&nbsp&nbsp missed率</b>
						&nbsp--&nbsp&nbsp{{current_task.stats.missed_rate}}
					</p>
				</li>
				<li>
				</li>
			</ul>
		</div>
		<hr>
	</div>
</div>
{% endblock %}
