from django.conf.urls import patterns, include, url
from django.contrib.auth.models import User
from django.contrib import admin

from rest_framework import routers, serializers, viewsets

from bafs import models
from bafs.views import chartdata

# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')

class TeamSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Team
        fields = ('id', 'name')
        
# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# ViewSets define the view behavior.
class TeamViewSet(viewsets.ModelViewSet):
    queryset = models.Team.objects.all()
    serializer_class = TeamSerializer


# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'teams', TeamViewSet)

admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'bafs.views.home', name='home'),
    url(r'^', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^admin/', include(admin.site.urls)),
)

# Consider refactor?
general_urls = patterns('bafs.views.general',
    url(r'^$', 'index'),                        
    url(r'^authorization$', 'authorization'),
    url(r'^join$', 'join'),

    url(r'^leaderboard/$', 'leaderboard'),
    url(r'^leaderboard/team/$', 'team_leaderboard'),
    url(r'^leaderboard/team_text/$', 'team_leaderboard_classic'),
    url(r'^leaderboard/team_various/$', 'team_leaderboard_varioius'),
    url(r'^leaderboard/individual/$', 'indiv_leaderboard'),
    url(r'^leaderboard/individual_text/$', 'indiv_leaderboard_classic'),
    url(r'^leaderboard/individual_various/$', 'indiv_leaderboard_various'),
    
    url(r'^explore/$', 'trends'),
    url(r'^explore/team_cumul/$', 'team_cumul_trend'),
    url(r'^explore/team_weekly/$', 'team_weekly_points'),
    url(r'^explore/indiv_elev_dist/$', 'indiv_elev_dist'),
    url(r'^explore/riders_by_lowtemp/$', 'riders_by_lowtemp'),
    
    url(r'^people/$', 'list_users'),
    url(r'^people/(?P<user_id>\w+)/$', 'show_user'),
    url(r'^/people/ridedays/$', 'ride_days'),
    
    url(r'^pointless/avgspeed/$', 'average_speed'),
    url(r'^pointless/avgdist/$', 'average_distance'),
    url(r'^pointless/billygoat/$', 'billy_goat'),
    url(r'^pointless/tortoiseteam/$', 'tortoise_team'),
    url(r'^pointless/weekend/$', 'wknd'),
    
)

urlpatterns += patterns('',
    url(r'^', include(general_urls)),
)

# Consider refactor?
extra_patterns = patterns('bafs.views.chartdata',
    url(r'^team_leaderboard/$', 'team_leaderboard_data'),
)

urlpatterns += patterns('',
    url(r'^chartdata/', include(extra_patterns)),
)