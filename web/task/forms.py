# -*- coding:utf-8 -*-

import json,re

from django import forms
from django.db import models
from django.forms import widgets


from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from mycron.task.models import Task

class TimeIntervalWidget(widgets.MultiWidget):
    def __init__(self, attrs=None):
        days = [(day, day) for day in (0, 1, 2, 3, 5, 7, 10, 15,30)]
        hours = [(hour, hour) for hour in (0, 1, 2, 3, 6, 12)]
        minutes = [(minute, minute) for minute in (0, 1, 3, 5, 10, 15, 20, 30, 45)]
        seconds = [(second, second) for second in (0, 5, 10, 30)]
        _widgets = (
            widgets.Select(attrs=attrs, choices=seconds),
            widgets.Select(attrs=attrs, choices=minutes),
            widgets.Select(attrs=attrs, choices=hours),
            widgets.Select(attrs=attrs, choices=days),
        )
        super(TimeIntervalWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        if value:
            value = json.loads(value)
            return [value["seconds"], value["minutes"], value["hours"], value["days"]]
        return [0, 5, 0, 0]

    def format_output(self, rendered_widgets):
        r = rendered_widgets
        return r[0]+u" 秒 " + r[1] +  u" 分钟 " + r[2] + u" 小时 " + r[3] +u"  天"

    def value_from_datadict(self, data, files, name):
        datelist = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)]

        data = {"seconds": int(datelist[0]), 'minutes': int(datelist[1]), 'hours':int(datelist[2]), 'days':int(datelist[3])}
        return json.dumps(data)

class CronWidget(widgets.MultiWidget):
    def __init__(self, attrs=None):
        self.field_keys = ('second', 'minute', 'hour', 'day_of_week', 'day', 'month', 'year')
        self.field_names = (u'秒', u'时', u'分', u'星期', u'日', u'月', u'年')


        _widgets = (
            widgets.TextInput(attrs=dict(attrs, **{'placeholder':'秒'})),
            widgets.TextInput(attrs=dict(attrs, **{'placeholder':"分"})),
            widgets.TextInput(attrs=dict(attrs, **{'placeholder':"时"})),
            widgets.TextInput(attrs=dict(attrs, **{'placeholder':"星期"})),
            widgets.TextInput(attrs=dict(attrs, **{'placeholder':"日"})),
            widgets.TextInput(attrs=dict(attrs, **{'placeholder':"月"})),
            widgets.TextInput(attrs=dict(attrs, **{'placeholder':"年"})),
        )
        super(CronWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        if value:
            return value.split(' ')
            #value = json.loads(value)
            #return [value[key] for key in self.field_keys]
        return [""] * 7

    def value_from_datadict(self, data, files, name):
        values = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)]
        values = ["*" if v.strip() == '' else v.strip() for v in values]
        return ' '.join(values)
        #data = dict(zip(self.field_keys, values))
        #return json.dumps(data)

#class TaskUrlWidget(widgets.MultiWidget):
    #def __init__(self, attrs=None):
        #methods = (('get', 'GET'), ('post', 'POST'))
        #_widgets = (
            #widgets.TextInput(attrs=attrs),
            #widgets.Select(attrs=attrs, choices=methods),
        #)
        #super(TaskUrlWidget, self).__init__(_widgets, attrs)

    #def decompress(self, value):
        #if value:
            #return [value.url, value.method]
        #return ['', 'get']



class TaskForm(forms.ModelForm):
    run_time_date = forms.CharField(label="运行时间", required=False, widget=widgets.DateTimeInput(attrs={'class':'ui_timepicker'}))
    run_time_interval= forms.CharField(label="运行间隔", required=False, widget=TimeIntervalWidget(attrs={'class':'select interval-time'}))
    run_time_cron= forms.CharField(label="Cron时间", required=False, widget=CronWidget(attrs={'style':'width:50px;text-align:center;'}),
                                   help_text="格式: `秒 |分 时 周 日 月 年`, 例如 `0 */1 7-10 * * * *` 表示每天7-10点之间，每隔1分钟执行一次")

    class Meta:
        model = Task
        widgets = {
            'discription': forms.Textarea(attrs={'cols':200, 'rows':2}),
            'run_params': forms.Textarea(attrs={'cols':200, 'rows':2}),
            'run_time':   forms.DateTimeInput(attrs={'class':'ui_timepicker'}),
            'run_type':   forms.Select(attrs={'style':"width:80px"}),
            'type':   forms.Select(attrs={'style':"width:100px"}),
        }
        fields = ['name', 'run_entry', 'run_type', 'run_params', 'type', 'run_time_date', 'run_time_interval',
                  'run_time_cron']
        hidden_fields = ['id']



    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_id = 'id-taskedit'
        self.helper.form_class = 'form-horizontal'
        self.helper.form_method = 'post'

        self.helper.add_input(Submit('submit', '保存'))
        super(TaskForm, self).__init__(*args, **kwargs)

    def clean(self):
        super(TaskForm, self).clean()
        #if not password1 and not password2 or password1 != password2:
            #raise forms.ValidationError("Passwords dont match")
        task_type = self.cleaned_data.get('type')
        run_time = self.cleaned_data.get('run_time_'+task_type, '').rstrip()
        if task_type == 'date':
            if run_time == '':
                raise forms.ValidationError("请填写任务的运行时间")
        elif task_type == 'interval':
            try:
                it = json.loads(run_time)
                if it['days']+it['hours']+it['minutes']+it['seconds']== 0:
                    raise
            except:
                raise forms.ValidationError("请填写任务的运行间隔")
        elif task_type == 'cron':
            p = re.compile('^(?:[0-9L\*\-\,\/]+ ){6}(?:[0-9L\*\-\,\/]+)$')
            if not p.match(run_time):
                raise forms.ValidationError("请填写合法的cron表达式'秒 分 时 周 日 月 年'")
                                            
            
        self.cleaned_data.update({'run_time': run_time})
        return self.cleaned_data
