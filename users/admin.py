from django.contrib import admin

from .models import Address, Message, Order, PointLedger, Profile, Skill


# Register your models here.
admin.site.register(Profile)
admin.site.register(Message)
admin.site.register(Skill)
admin.site.register(Address)
admin.site.register(Order)
admin.site.register(PointLedger)
