# -*- coding: utf-8 -*-

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages

from django.forms import ValidationError

import cgi
import logging


from mycron.task.models import Task
from mycron.task.forms import TaskForm

logger = logging.getLogger('cron.frontend')

def index(request):
    '''
    task list
    '''
    if request.method != 'GET':
        return HttpResponse(status=400)

    size  = 10
    page  = request.GET.get('page', 1)
    page  = int(page)
    
    start = (page-1) * size
    end   = start+size

    try:
        tasks = Task.objects.order_by('-id')[start : end]
        total = Task.objects.count()
    except Exception:
        logger.exception("index tasks failed")
        messages.error(request, "查询失败")

    context = {'tasks': tasks, 'pagination': {'total':total, 'page': page-1, 'keywords':''}}
    return render(request, 'task/index.tpl', context)

def getRunTime(task_type, request):
    p = request.POST
    try:
        task_type       = p["task_type"].strip()
        if task_type not in ['date', 'cron', 'interval']:
            raise "task type is invalid"
    except:
        run_time   = p["run_time"].strip()
        if task_type == 'date':
            run_time = "%s %s" % (p['date_date'], p['date_time'])
        elif task_type == 'interval':
            values =["%s %s" % (p[key], key[8:]) for key in ['interval_days', 'interval_hours', 'interval_minutes', 'interval_seconds'] if int(p[key]) > 0]
            run_time  = values.join('|')
        elif task_type == "cron":
            cron_time = p['cron_ime']
            if len(cron_time.split(" ")) != 7:
                raise "cron value error"
            run_time = cron_time

    return run_time



def create(request):
    if request.method == 'GET':
        form = TaskForm()
        form.helper.form_action = '/task/create'
        context = {'form':form}
        return render(request, 'task/new.tpl', context)

    if request.method != 'POST':
        return HttpResponse(status=400)

    form = TaskForm(request.POST)
    try:
        if form.is_valid():
            task = form.save(commit=False)
            task.run_time = form.cleaned_data['run_time']
            task.save()
        else:
            raise ValidationError(form.errors)
    except (ValidationError, ValueError):
        logger.exception('create task failed: validated error')
        return render(request, 'task/new.tpl', {"form":form})
    except Exception:
        logger.exception('create task failed')
        messages.error(request, '任务创建失败')
        return render(request, 'task/new.tpl', {"form":form})

    messages.success(request, '任务创建成功')
    return HttpResponseRedirect("/task/index")

def update(request):
    '''
    edit task
    '''
    if request.method == 'GET':
        task_id = int(request.GET['id'])
        result = '任务(id=%d)' % task_id
        try:
            task = Task.objects.get(pk = task_id)
            key = "run_time_"+task.type
            initial = {key : task.run_time}
            form = TaskForm(instance=task, initial=initial)
            form.helper.form_action = '/task/update?id=%d' % task_id 
        except ObjectDoesNotExist:
            logger.warn('edit task %d failed: task does not exist' % (task_id))
            messages.error(request, result + "不存在")
            return HttpResponseRedirect('/task/index')
        except Exception:
            logger.exception('edit task %d failed' % (task_id))
            messages.error(request, result + '编辑失败' )
            return HttpResponseRedirect('/task/index')

        context = {"task":task, 'form':form}
        return render(request, 'task/edit.tpl', context)

    elif request.method != 'POST':
        return HttpResponse(status=400)

    try:
        task_id = int(request.REQUEST.get('id', 0))
        result = '任务(id=%d)' % task_id
        task = Task.objects.get(pk=task_id)
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save(commit=False)
            task.run_time = form.cleaned_data['run_time']
            task.save()
        else:
            raise ValidationError()
    except ObjectDoesNotExist:
        logger.warn(request, 'update task (id=%d) failed: task not exist' % task_id)
        messages.warn(request, result+"不存在")
        return HttpResponseRedirect('/task/index')
    except ValidationError:
        logger.exception('update task(id=%d) failed: task validate failed' % task_id)
        messages.error(request, result+"验证失败")
        return render('task/edit', {'form':form})
    except Exception:
        logger.exception('update task(id=%d) failed' % (task_id))
        messages.error(request, result+"修改失败")
        return render('task/edit', {'form':form})

    messages.success(request, result+'修改成功')
    return HttpResponseRedirect('/task/show?id=%d' % task_id)

def show(request):
    task_id = int(request.REQUEST.get('id', 0))
    try:
        task = Task.objects.get(pk=task_id)
    except ObjectDoesNotExist:
        logger.warn('show task %d failed: task does not exist' % (task_id))
        messages.error(request, '任务不存在')
        return HttpResponseRedirect('/task/index')
    except:
        logger.exception('show task %d failed' % (task_id))
        messages.error(request, '显示任务(%d)失败' % task_id)
        return HttpResponseRedirect('/task/index')

    context = {"current_task":task}
    return render(request, 'task/show.tpl', context)

def destroy(request):
    if request.method != 'POST':
        messages.error(request, '亲，这样删除很危险')
        return HttpResponseRedirect('/task/index')

    task_id = int(request.POST.get('id', 0))
    try:
        task = Task.objects.get(pk = task_id)
        task.delete()
        result = '任务(id=%d)删除成功' % task_id
        messages.success(request, result)
    except ObjectDoesNotExist:
        logger.warn('delete task %d failed: task does not exist' % (task_id))
        result = '任务(id=%d)不存在' % task_id
        messages.error(request, result)
    except:
        logger.exception('destroy task %d failed' % (task_id))
        result = '任务(id=%d)删除失败' % task_id
        messages.error(request, result)

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        return HttpResponse(result);
    else:
        return HttpResponseRedirect('/task/index')

def toggleStatus(request):
    task_id = int(request.GET.get('id', 0))
    result = '任务(id=%d)' % task_id
    try:
        task = Task.objects.get(pk = task_id)
        if task.isActive():
            task.disable()
        else:
            task.enable()

        result +=  '状态改变成功'
        messages.success(request, result)
    except ObjectDoesNotExist:
        logger.warn('change task %d status failed: task does not exist' % (task_id))
        result +=  '不存在'
        messages.error(request, result)
    except:
        logger.exception('change task %d status failed' % (task_id))
        result +=  '状态改变失败'
        messages.error(request, result)

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        return HttpResponse(result);
    else:
        return HttpResponseRedirect('/task/index')

def run(request):
    task_id = int(request.POST.get('id', 0))
    try:
        task = Task.objects.get(pk = task_id)
        result=task.run()
        resultStr=cgi.escape(result)
    except ObjectDoesNotExist:
        messages.error(request, '任务(id=%d)不存在' % task_id)
        logger.warn('run task %d failed: task does not exist' % (task_id))
    except:
        logger.exception('run task %d failed' % (task_id))
        messages.error(request, '立即运行失败')

    if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
        return HttpResponse(resultStr);
    else:
        return HttpResponseRedirect('/task/index')

def search(request):
    keywords = request.GET.get('keywords', '')
    keywords = keywords.strip()
    if len(keywords) == 0:
        return HttpResponseRedirect('/task/index')

    size  = 10
    page  = request.GET.get('page', 1)
    page  = int(page)
    
    start = (page-1) * size
    end   = start+size

    try:
        items = Task.objects.search(keywords)
        total = items.count()
        tasks = items[start:end]
    except:
        messages.error(request, "查询失败")

    context = {'tasks': tasks, 'pagination': {'total':total, 'page': page-1, 'keywords':keywords}}
    return render(request, 'task/index.tpl', context)
