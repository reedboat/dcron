{% extends "_layout/application.tpl" %}
{% load datetype %}
{% block title %} 任务列表 {%endblock%}
{% block styles %>
{% endblock %>
{% block scripts%}

    <script src="/static/js/lib/jquery.pagination.js"> </script>
	<script src="/static/js/lib/bootbox.js"> </script>
   

   <script type="text/javascript">
    $(function(){
        $('.pagination').pagination({{pagination.total}},{'num_display_entries':5, items_per_page:10, current_page: {{pagination.page}}, 
            callback:function(page,component){
                if (page >= 0){
                    location.href='/task/index?page='+(page+1);
                }
                else {
                    return false;
                }
            }
        });
        $(".btn.delete").click(function(e){
            var task_id = $(e.target).closest("tr").data("id");
            bootbox.confirm("确认删除?", "取消", "确定", function(confirmed) {
                if(confirmed) {
                    $.post("/task/destroy", {'id':task_id}, function(resp){
                        location.reload();
                    });
            }
            });		
            return false;
        })
		$(".btn.runNow").click(function(e){
            var task_id = $(e.target).closest("tr").data("id");
            bootbox.confirm("确认立即运行?", "取消", "确定", function(confirmed) {
                if(confirmed) {
                    $.post("/task/run", {'id':task_id}, function(resp){
                        bootbox.alert(resp);
                    });
            }
            });		
            return false;
        })
    });
    </script>
	
{% endblock%}

{% block content %}
  <h2>任务列表</h2>
  <hr />
  <form method=get class="navbar-search pull-right" action="/task/search?">
	<input type="text" name="keywords" class="search-query" style="margin-bottom:10px;" placeholder="Search">
	<button type="submit" class="btn" style="margin-bottom:10px;">搜索</button>
  </form>
  <br>
  <style type="text/css">
	.container {width:95%;min-width:960px;}
  </style>
  <table class="table table-bordered table-striped table-hover table-condense">
    <thead>
    <tr>
        <th>#</th>
        <th>id</th>
        <th>名称</th>
        <th>类型</th>
        <th>运行时间</th>
        <th>URL</th>
        <th>状态</th>
        <th>操作</th>
    </tr>
    </thead>
   <tbody>
     
    {% for task in tasks %}
    <tr data-id="{{task.id}}">
        <td><input type="checkbox" name="selectlist[]" class=selectlist value={{task.id}}></td>
        <td>{{task.id}}</td>
        <td><a href="/task/show?id={{task.id}}">{{task.name}}</a></td>
		{% if task.type == "date" %}
			<td>{{"单次"}}</td>
			<td>{{task.run_time}}</td>
		{% elif task.type == "interval" %}
			<td>{{"间隔"}}</td>
			<td>{{task.run_time|transdate}}</td>
		{% elif task.type == "cron" %}
			<td>{{"CRON"}}</td>
			<td>{{task.run_time}}</td>
		{% endif %}
 

        <td>{{task.run_entry}}</td>
        <td>
		{% if task.status == "finished" %}
			{{"已结束"}}
		{% elif task.status == "normal" %}
			{{"正常"}}
		{% elif task.status == "disabled" %}
			{{"过期"}}
		{% endif %}
		</td>
        <td><a href="/task/update?id={{task.id}}" class="btn" >修改</a> 
		    <a class="btn runNow">立即运行</a>  
            <a class="btn delete">删除</a>  
		    <a href="/task/toggleStatus?id={{task.id}}" class="btn">
			{% if task.active == 1 %}
			{{"停用"}}
		    {% elif task.active == 0 %}
			{{"启用"}}
		    {% endif %}
		    </a>
        </td>
    </tr>
    {%endfor%}
  
 </tbody>
 </table>
<div class="pagination"></div>
{% endblock %}
