<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
    <head>
        <title>{%block title %}{%endblock%} -- 定时任务管理系统</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta http-equiv="X-UA-Compatible" content="IE=EDGE" />
        <meta charset="utf-8" />
        <link href="/static/css/lib/bootstrap.css" rel="stylesheet" media="screen"/>
        <style>
            body {
                padding-top: 60px; /* 60px to make the container go all the way to the bottom of the topbar */
            }
        </style>
        <link href="/static/css/lib/bootstrap-responsive.css" rel="stylesheet" />
        <!-- HTML5 shim, for IE6-8 support of HTML5 elements -->
        <!--[if lt IE 9]>
          <script src="/static/js/lib/html5shiv.js"></script>
        <![endif]-->
        <link rel="shortcut icon" href="/static/favicon.ico"/>     
        <script src="/static/js/lib/jquery.min.js"> </script>
        {% block styles %}
        {%endblock%}
        <link href="/static/css/cron.css" rel="stylesheet" media="screen"/>
    </head>
    <body>

        {%block header%}
        <div class="navbar navbar-inverse navbar-fixed-top">
            <div class="navbar-inner">
                <div class="container">
                    <button type="button" class="btn btn-navbar" data-toggle="collapse" data-target=".nav-collapse">
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                        <span class="icon-bar"></span>
                    </button>
                    <a href="#" class="brand">定时任务管理系统</a>
                    <div class="nav-collapse collapse">
                        <ul class="nav">
                            <li>
                                <a href="/task/create">添加任务</a>
                            </li>
                            <li>
                                <a href="/task/index">任务列表</a>
                            </li>
                        </ul>
                        <ul class="pull-right nav">
                            <li><a>{{g_username}}</a></li>
                            <li><a class="exit" href="">退出</a></li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        {%endblock%}

        <div class="container">
            {% if messages %}
              {% for message in messages %}
                    <ul class="alert alert-block alert-{{message.tags}}">
                      <li>{{ message }}</li>
                    </ul>
              {% endfor %}
            {% endif %}

            {%block content%}
            {%endblock%}
        </div>

        {%block footer%}
        {%endblock%}
        <script src="/static/js/lib/bootstrap.min.js"> </script>
        {% block scripts %}
        {%endblock%}
    </body>
</html>
