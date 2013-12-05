#coding:utf-8
from django import template
import json

register = template.Library()

@register.filter(name="transdate")
def transdate(value):
	try:
		date=json.loads(value)
		names = {"days":"天", "hours":"小时", "minutes":"分钟", "seconds":"秒"}
		keys = ["days", "hours", "minutes", "seconds"]
		s=''
		for key in keys:
			if date[key] != 0:
				s+=str(date[key]) + names[key]
	except:
		return value
	return s