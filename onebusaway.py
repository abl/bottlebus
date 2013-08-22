import logging
log = logging.getLogger()
logging.basicConfig(format='[%(levelname)-8s] %(message)s')
log.setLevel(logging.DEBUG)

import urllib2
from urllib import urlencode
try:
    import ujson as json
except ImportError:
    log.warn("Could not import ujson; falling back to regular (slow) json")
    import json

ENDPOINT = 'http://api.onebusaway.org/api/'

class OneBusAway:
    def __init__(self, key):
        self._key = key

    def stopsForLocation(self, lat, lon, radius=250):
        args = locals()
        del args['self']
        args['key'] = self._key
        URI = '%swhere/stops-for-location.json?%s' % (ENDPOINT, urlencode(args))
        data = json.load(urllib2.urlopen(URI))
        stops = data['data']['stops']
        return [str(y[1]) for y in sorted([((x['lat']-lat)**2+(x['lon']-lon)**2, x['id']+":"+x['direction']+":"+x['name'].replace(" & ", "\n")) for x in stops], key=lambda x:x[0])]

    def arrivalsAndDeparturesForStop(self, stop):
        URI = '%swhere/arrivals-and-departures-for-stop/%s.json?key=%s' % (ENDPOINT, stop, self._key)
        data = json.load(urllib2.urlopen(URI))
        ctime = data['currentTime']
        arrivals = data['data']['arrivalsAndDepartures']
        for x in arrivals:
            at = x['predictedArrivalTime']
            if at == 0:
                at = x['scheduledArrivalTime']
            x['minutesToArrival'] = ((at - ctime)/6000+5)/10
        return sorted([(x['routeShortName'], x['minutesToArrival']) for x in arrivals], key=lambda x:x[1])
