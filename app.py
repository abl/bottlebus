import gevent.monkey; gevent.monkey.patch_all()
from bottle import run, request, post
import os
import logging
import onebusaway
import sys

log = logging.getLogger()
logging.basicConfig(format='[%(levelname)-8s] %(message)s')
log.setLevel(logging.DEBUG)


#TODO: This will come in handy once we start using Sqlite; for now, it's just a note-to-self.
#VENV_PATH = None

#try:
#    VENV_PATH = os.environ['VIRTUAL_ENV']
#except:
#    log.warn("Unable to determine virtualenv path (VIRTUAL_ENV not set); defaulting to current directory")
#    VENV_PATH = '.'

#plugin = bottle.ext.sqlite.Plugin(dbfile=os.path.join(VENV_PATH, 'bottlebus.db'))
#app.install(plugin)

api = onebusaway.OneBusAway(key=os.environ['ONEBUSAWAY_KEY'])

#A little bit of sugar.
#Let's assume that every request has parameters in the order that they are expected.
#Let's further assume that every request's parameters are densely keyed; 1,2,3 not 3,8,10
#This function maps incoming pebble requests to the relevant arguments.
#Further, let's assume that every function returns an array.
#Let's send back to the pebble a simple encoding:
#1: ["B', len(array)]
#2: array[0]
#n: array[n-2]
#TODO: This assumes all returns are string arrays
#TODO: Should probably special-case 'id' and 'db' parameters
#TODO: Automatic paging; will come after sqlite and other bits.
MAX_REQUEST_SIZE = 90 #TODO: This looks like it'll need trial and error...
def pebbleize(function):
    def inner():
        pebbleId = request.headers.get('X-Pebble-ID')
        data = request.json
        argc = function.func_code.co_argcount-1 #ID is always the first parameter
        name = function.func_code.co_name
        if data is None:
            log.error("Invalid request data - couldn't get JSON")
            return None #TODO: Error codes.
        if len(data) != argc:
            log.error("Argument count mismatch calling %s - expected %d got %d" % (name, argc, len(data)))
            return None #TODO: Come up with a reasonable error code return mechanism.
        args = []
        for key in xrange(argc):
            k = str(key+1)
            args.append(data[k])
        array = function(pebbleId, *args)

        output = {}
        total = 0
        i = 1
        while len(array):
            v = array.pop(0)
            s = len(v)+7 #TODO: 4 bytes for the key overhead?
            if total+s > MAX_REQUEST_SIZE:
                log.warn("Had to truncate request to %s made by %s: %d value(s) cut off" % (name, pebbleId, len(array)+1))
                break
            i+=1
            total += s
            output[str(i)] = v

        output['1'] = i-1
        return output

    return inner

@post('/stops')
@pebbleize
def postStops(id, lat, lon):
    log.info("postStops: id:%s lat:%s lon:%s" % (id, lat, lon))
    lat /= 10000000.
    lon /= 10000000.
    return api.stopsForLocation(lat, lon)

@post('/arrivals')
@pebbleize
def postArrivals(id, stop, filter):
    log.info("postStops: id:%s stop:%s filter:%s" % (id, stop, filter))
    if filter == 0:
        return [":".join([str(y) for y in x]) for x in api.arrivalsAndDeparturesForStop(stop)]
    else:
        return [":".join([str(y) for y in x]) for x in api.arrivalsAndDeparturesForStop(stop) if x[0] == filter]

if __name__=="__main__":
    run(server='gevent', host='0.0.0.0', port=os.environ.get('PORT', 8080))
