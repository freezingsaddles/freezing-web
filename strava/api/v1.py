from datetime import datetime

import requests

from strava.api import BaseServerProxy

class V1ServerProxy(BaseServerProxy):
    """
    
    """
    
    def get_club(self, club_id):
        """
        Return V1 object structure for club
        
        {"club":{"description":"Mission Cycling is devoted to the enjoyment of one of the world's purest, most classic sporting endeavors: Cycling. Our aim is simple: to enjoy the unique challenges and rewards offered by experiencing our unique countryside from the saddle of a bike.",
          "name":"Mission Cycling",
          "location":"San Francisco, CA",
          "club_id":15}
        }
        
        :param club_id: The club_id of the club to fetch.
        """
        response = self._get("http://{}/api/v1/clubs/{}".format(self.server, club_id))
        return response['club']
        
    def get_ride(self, ride_id):
        """
        Return V1 object structure for ride.
        
        {"ride":{"id":11280631,
                 "startDate":"2012-06-20T11:10:00Z",
                 "startDateLocal":"2012-06-20T07:10:00Z",
                 "timeZoneOffset":-18000,
                 "elapsedTime":3000,
                 "movingTime":3000,
                 "distance":25588.6,
                 "averageSpeed":8.529533333333333,
                 "averageWatts":null,
                 "maximumSpeed":0.0,
                 "elevationGain":0,
                 "location":"Arlington, VA",
                 "name":"Morning Commute - computer malfunction?",
                 "bike":{"id":67845,"name":"Commuter/Cross"},
                 "athlete":{"id":182475,"name":"Hans Lellelid","username":"hozn"},
                 "description":"",
                 "commute":true,
                 "trainer":false}}
        
        :param ride_id: The ride_id of ride to fetch.
        """
        url = "http://{}/api/v1/rides/{}".format(self.server, ride_id)
        return self._get(url)['ride']
        
    def list_rides(self, **kwargs):
        """
        Enumerate rides for specified attribute/value.
        
        :keyword clubId: Optional. Id of the Club for which to search for member's Rides.
        :keyword athleteId: Optional. Id of the Athlete for which to search for Rides.
        :keyword athleteName: Optional. Username of the Athlete for which to search for Rides.
        :keyword startDate: Optional. Day on which to start search for Rides.  The date is the local time of when the ride started.
        :keyword endDate: Optional. Day on which to end search for Rides. The date is the local time of when the ride ended.
        :keyword startId: Optional. Only return Rides with an Id greater than or equal to the startId.
        """
        # Dates should be formatted YYYY-MM-DD.  They are in local time of ride, so we ignore TZ
        for datefield in ('startDate', 'endDate'):
            if datefield in kwargs and isinstance(kwargs[datefield], datetime):
                kwargs[datefield] = kwargs[datefield].strftime('%Y-%m-%d')
                
        url = "http://{}/api/v1/rides".format(self.server)
        response = self._get(url, params=kwargs)
        return response['rides']