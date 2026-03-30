from django.contrib import admin
from .models import Place, Checkin, Friendship, PointEvent

admin.site.register(Place)
admin.site.register(Checkin)
admin.site.register(Friendship)
admin.site.register(PointEvent)