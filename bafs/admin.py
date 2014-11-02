from django.contrib import admin

from bafs import models

class TeamAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id',)

def team_name(obj):
    return obj.team.name
team_name.short_description = 'Team'
team_name.admin_order_field = 'team__name'

class AthleteAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'team')
    list_display_links = ('id', 'name')    
    
class RideAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'start_date', 'distance')
    list_display_links = ('id', 'name')
    
class RideEffortAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Team, TeamAdmin)
admin.site.register(models.Athlete, AthleteAdmin)
admin.site.register(models.Ride, RideAdmin)
admin.site.register(models.RideEffort, RideEffortAdmin)
