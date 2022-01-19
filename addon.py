import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import re, sys, os, time, re
import simplecache
import urllib, urllib.parse
import json
import datetime

dialog = xbmcgui.Dialog()
win = xbmcgui.Window(10000)
_cache = simplecache.SimpleCache()

def disp_notification(type):
    addon = xbmcaddon.Addon("script.epg_fuzzy_match")
    notification_enabled = addon.getSetting('notification_enabled')
    no_match_notification_enabled = addon.getSetting('no_match_notification_enabled')
    if notification_enabled == 'false':
       return ''

    if type == 'Multi':
       message = 'Found Multiple Matches'
    elif type == 'Single':
        message = 'Found Single Match'
    else:
        if no_match_notification_enabled == 'false':
           return ''
        message = 'No Matches Found'

    dialog.notification('EPG Match', message, xbmcgui.NOTIFICATION_INFO, 100)

def debug_log(message):
    debug = 'EPG Fuzzy Match: ' + message
    xbmc.log(debug, level=xbmc.LOGINFO)

def monitorgui():

    # gather all the pieces to uniquely identify 
    # the current item highlighted in guide
    
    d = {
        "title" : xbmc.getInfoLabel("ListItem.EpgEventTitle"),
        "imdbnumber" : xbmc.getInfoLabel("ListItem.IMDBNumber"),
        "year" : xbmc.getInfoLabel("ListItem.Year"),
        "season" : xbmc.getInfoLabel("ListItem.Season"),
        "episode" : xbmc.getInfoLabel("ListItem.Episode"),
        "rel_date" : xbmc.getInfoLabel("ListItem.ReleaseDate"),
        "org_date" : xbmc.getInfoLabel("ListItem.OriginalDate"),
        "prem_date" : xbmc.getInfoLabel("ListItem.Premiered"),
        "ep_name" : xbmc.getInfoLabel("ListItem.EpisodeName"),
        "status" : xbmc.getInfoLabel("ListItem.Status")
    }
    
    
    if not d['season']:
        d['season'] = -1

    if not d['episode']:
        d['episode'] = -1
            
    # build cache id
    this_cache_id = 'EPG_Match8.'
    for x in d:
        this_cache_id = this_cache_id + '|' + str(d[x])
    
    # if it matches current processed data, then just return
    if win.getProperty('Fuzzy.cache_id') == this_cache_id:
        return
       
    # starting a new lookup, set new cache property
    win.setProperty("Fuzzy.cache_id", this_cache_id)
    
    # check if data is already cached
    mycache = _cache.get(this_cache_id)
    
    if mycache:
       # cache data exists, set properties and return
       
       win.setProperty("Fuzzy.context", mycache[0])
       win.setProperty("Fuzzy.label", mycache[1])
       win.setProperty("Fuzzy.xsp", mycache[2])
       _cache.set( this_cache_id, mycache, expiration=datetime.timedelta(days=1))
       disp_notification(mycache[0])
       debug = 'cache_hit: %s' % (this_cache_id)
       debug_log(debug)
       
       debug = 'cache_results: %s : %s : %s' % (mycache[0], mycache[1], mycache[2])
       debug_log(debug)
       
       
       return
    
    # new lookup required, determine if a movie or a series
    if int(d['season']) > -1 or int(d['episode']) > -1 or not d['ep_name'] == '':
        debug = 'is a series: %s' % (this_cache_id)
        debug_log(debug)
        search_series(this_cache_id,**d)

        mycache = []
        
        mycache.append(win.getProperty('Fuzzy.context'))
        mycache.append(win.getProperty('Fuzzy.label'))
        mycache.append(win.getProperty('Fuzzy.xsp'))
         
        debug = 'cache_store: %s' % (mycache)
        debug_log(debug)
        
        _cache.set( this_cache_id, mycache, expiration=datetime.timedelta(days=1))      
    
    
    elif not d['title']:
        debug = 'no title: %s' % (this_cache_id)
        debug_log(debug)
        no_match()
    elif not d['year']:
        debug = 'no year: %s' % (this_cache_id)
        debug_log(debug)
        no_match()
    else:
        debug = 'is a movie: %s' % (this_cache_id)
        debug_log(debug)
        search_movies(this_cache_id,**d)
        
        mycache = []
        
        mycache.append(win.getProperty('Fuzzy.context'))
        mycache.append(win.getProperty('Fuzzy.label'))
        mycache.append(win.getProperty('Fuzzy.xsp'))
         
        debug = 'cache_store: %s' % (mycache)
        debug_log(debug)
        
        _cache.set( this_cache_id, mycache, expiration=datetime.timedelta(days=1))    


def no_match():
    win.setProperty("Fuzzy.context", "")
    win.setProperty("Fuzzy.xsp", "")
    win.setProperty("Fuzzy.label", "")
    return

def search_series(cache_id, **kwargs):
    search_title = kwargs.get('title')
    search_imdbnumber = kwargs.get('imdbnumber')
    search_episode_title = kwargs.get('ep_name')
    search_season = kwargs.get('season')
    search_episode = kwargs.get('episode')

    ct_title = re.sub("[^0-9a-zA-Z]+", " ", search_title)
    ct_title = re.sub(" {2}", " ", ct_title)
   
    debug = 'Series Cleaned: ' + ct_title
    debug_log(debug)

    search_series_parts = re.split(" ", ct_title)
    
    title_filter = ''

    for part in search_series_parts:
        if title_filter != '':
            title_filter = title_filter + ','

        title_filter = title_filter + '{"field": "title", "operator": "contains", "value": "' + part + '"}'



    command = '{"jsonrpc": "2.0", ' \
            '"method": "VideoLibrary.GetTVShows", ' \
            '"params": { ' \
            '"filter": { "and": [ %s ]}, ' \
            '"sort": { "order": "ascending", "method": "label" }, ' \
            '"properties": ["title", "imdbnumber", "year", "file", "premiered"] ' \
            '}, "id": 1}' % (title_filter)

    debug = 'JSON sent: ' + command
    debug_log(debug)

    result = json.loads(xbmc.executeJSONRPC(command))
    matches = result['result']['limits']['total']
    match_type = 'None'
    tvshowid = ''
    
    for i in range(0, result['result']['limits']['total']):
        
        cr_title = result['result']['tvshows'][i]['title']
        cr_title = re.sub("[^0-9a-zA-Z]+", " ", cr_title)
        cr_title = re.sub(" {2}", " ", cr_title)

        if result['result']['tvshows'][i]['imdbnumber'] == search_imdbnumber and search_imdbnumber != '':
            # exact imdb match, only display this one
            tvshowid = result['result']['tvshows'][i]['tvshowid']
            match_type = 'imdb'
            break
        elif result['result']['tvshows'][i]['title'] == search_title:
            # exact title match, only display this one
            tvshowid = result['result']['tvshows'][i]['tvshowid']
            match_type = 'title'
            break
        elif ct_title == cr_title and match_type != 'imdb' and match_type != 'title':
            tvshowid = result['result']['tvshows'][i]['tvshowid']
            match_type = 'fuzzy'           


    if match_type == 'None' or tvshowid == '':
        no_match()
        return ''

    debug = 'Found a match via %s , tvshowid: %s' % (match_type, tvshowid)
    debug_log(debug)
    
    # now use tvshowid to see if this episode is found by SE or name
    
    command = '{"jsonrpc": "2.0", ' \
            '"method": "VideoLibrary.GetEpisodes", ' \
            '"params": { ' \
            '"tvshowid": %s, ' \
            '"properties": ["season", "episode", "firstaired", "originaltitle", "file"] ' \
            '}, "id": 1}' % (tvshowid)

    debug = 'JSON sent: ' + command
    debug_log(debug)    
    

    result = json.loads(xbmc.executeJSONRPC(command))
    matches = result['result']['limits']['total']
    files = []
    match_type = 'None'
    
    for i in range(0, result['result']['limits']['total']):

        cr_title = result['result']['episodes'][i]['originaltitle']
        cr_title = re.sub("[^0-9a-zA-Z]+", " ", cr_title)
        cr_title = re.sub(" {2}", " ", cr_title)

        if result['result']['episodes'][i]['season'] == search_season and result['result']['episodes'][i]['episode'] == search_episode:
            # SE match
            files.append(result['result']['episodes'][i]['file'])
            match_type = 'SE'
        elif result['result']['episodes'][i]['originaltitle'] == search_episode_title:
            # exact title match, only display this one
            files.append(result['result']['episodes'][i]['file'])
            match_type = 'title'
        elif ct_title == cr_title:
            files.append(result['result']['episodes'][i]['file'])
            match_type = 'fuzzy'           
    

    if len(files) > 0:
      
        xsp = '{"rules":{"or":['


        for i in range(0, len(files)):
            if i > 0:
                xsp = xsp + ","
            xsp = xsp + '{"field":"filename","operator":"is","value":"%s"}' % (files[i])
            file_path = files[i]

        xsp = xsp + ']},"type":"tvshows"}'

        xsp = urllib.parse.quote_plus(xsp)

        if i > 0:
            # indicate multi matches, set context to send to list of matches, trigger notification of such
            disp_notification('Multi')
            win.setProperty("Fuzzy.context", "Multi")
            win.setProperty("Fuzzy.xsp", xsp)
         
        else:
            # indicate 1 match, set context to go to dialogvideoinfo window, trigger notification of such
            disp_notification('Single')
            win.setProperty("Fuzzy.context", "Single")
            win.setProperty("Fuzzy.label",search_title)
            win.setProperty("Fuzzy.xsp", file_path)
            
        return 

    # no matches, no context menu addition, trigger notification of no match(es) found
    no_match()
    # finally, set cache
    
    
    
    
    
    
    

def search_movies(cache_id, **kwargs):
    # sometimes PVR title may include year,
    # if so, "clean" the title and grab that year
    # in case actual Year field empty or different
    
    search_raw = kwargs.get('title')
    search_year = kwargs.get('year')
    search_imdbnumber = kwargs.get('imdbnumber')
    x = re.split("\(", search_raw, 1)
    search_movie = str(x[0]).strip()
    y = len(x)
    if y == 2:
        y = re.split("\)", x[1], 1)
        y[0] = re.sub("[^0-9]+", "", y[0])
        if y[0]:
            if int(y[0]) > 1900 and int(y[0]) < 2100:
                split_year = int(y[0])
    
    if search_year == '':
        search_year = split_year
        
    if (search_movie == '' or search_year == '') and search_imdbnumber == '':
        no_match()
        debug = 'Movie missing title (%s) or year (%s) and no imdbnumber for cache: %s' % (search_movie, search_year, cache_id)
        debug_log(debug)
        return

    search_result = lib_search(cache_id, search_movie, search_year, search_imdbnumber, **kwargs)
    # returns: match_type, files

    if len(search_result[1]) > 0:
      
        xsp = '{"rules":{"or":['
      
        files = search_result[1]

        for i in range(0, len(files)):
            if i > 0:
                xsp = xsp + ","
            xsp = xsp + '{"field":"filename","operator":"is","value":"%s"}' % (files[i])
            file_path = files[i]

        xsp = xsp + ']},"type":"movies"}'

        xsp = urllib.parse.quote_plus(xsp)

        if i > 0:
            # indicate multi matches, set context to send to list of matches, trigger notification of such
            disp_notification('Multi')
            win.setProperty("Fuzzy.context", "Multi")
            win.setProperty("Fuzzy.xsp", xsp)
         
        else:
            # indicate 1 match, set context to go to dialogvideoinfo window, trigger notification of such
            disp_notification('Single')
            win.setProperty("Fuzzy.context", "Single")
            win.setProperty("Fuzzy.label",search_movie)
            win.setProperty("Fuzzy.xsp", file_path)
            
        return 

    # no matches, no context menu addition, trigger notification of no match(es) found
    no_match()
    # finally, set cache
    



def lib_search(cache_id, search_movie, search_year, search_imdbnumber, **kwargs):

    min_year = int(search_year) - 2
    max_year = int(search_year) + 2

    ct_movie = re.sub("[^0-9a-zA-Z]+", " ", search_movie)
    ct_movie = re.sub(" {2}", " ", ct_movie)
   
    debug = 'Movie Cleaned: ' + ct_movie
    debug_log(debug)

    search_movie_parts = re.split(" ", ct_movie)
    
    title_filter = ''

    for part in search_movie_parts:
        if title_filter != '':
            title_filter = title_filter + ','

        title_filter = title_filter + '{"field": "title", "operator": "contains", "value": "' + part + '"}'

    if search_imdbnumber != '':
        imdb_filter = '{"field": "imdbnumber", "operator": "is", "value": "%s"}' % (search_imdbnumber)

    if search_imdbnumber != '':
        command = '{"jsonrpc": "2.0", ' \
            '"method": "VideoLibrary.GetMovies", ' \
            '"params": { ' \
            '"filter": { "or" : [{"and": [%s]},%s] }, ' \
            '"sort": { "order": "ascending", "method": "label" }, ' \
            '"properties": ["title", "imdbnumber", "year", "file"] ' \
            '}, "id": 1}' % (title_filter, imdb_filter)
    else:
        command = '{"jsonrpc": "2.0", ' \
            '"method": "VideoLibrary.GetMovies", ' \
            '"params": { ' \
            '"filter": { "and": [ %s ]}, ' \
            '"sort": { "order": "ascending", "method": "label" }, ' \
            '"properties": ["title", "imdbnumber", "year", "file"] ' \
            '}, "id": 1}' % (title_filter)

    debug = 'JSON sent: ' + command
    debug_log(debug)

    result = json.loads(xbmc.executeJSONRPC(command))
    matches = result['result']['limits']['total']
    files = []
    match_type = 'None'
    
    for i in range(0, result['result']['limits']['total']):
        
        cr_movie = result['result']['movies'][i]['title']
        cr_movie = re.sub("[^0-9a-zA-Z]+", " ", cr_movie)
        cr_movie = re.sub(" {2}", " ", cr_movie)

        if result['result']['movies'][i]['imdbnumber'] == search_imdbnumber and search_imdbnumber != '':
            # exact imdb match, only display this one
            files = [result['result']['movies'][i]['file']]
            match_type = 'imdb'
            break
        elif result['result']['movies'][i]['title'] == search_movie:
            # exact title match, check year
            if result['result']['movies'][i]['year'] == search_year:
                files = [result['result']['movies'][i]['file']]
                match_type = 'title-year'
                break
            elif result['result']['movies'][i]['year'] > min_year \
                and result['result']['movies'][i]['year'] < max_year:
                # year +/- limits, so add to list and don't break
                files.append(result['result']['movies'][i]['file'])
                match_type = 'title-fuzzy_year'
        elif ct_movie == cr_movie:
            # cleaned title match
            if result['result']['movies'][i]['year'] == search_year:
                files = [result['result']['movies'][i]['file']]
                match_type = 'fuzzy_title-year'
            elif result['result']['movies'][i]['year'] > min_year \
                and result['result']['movies'][i]['year'] < max_year:
                # year +/- limits, so add to list and don't break
                files.append(result['result']['movies'][i]['file'])
                match_type = 'fuzzy_title-fuzzy_year'            

    # completed search, act on results
    
    match_return = [match_type, files]

    return match_return


if __name__ == '__main__':

    monitor = xbmc.Monitor()
    xbmc.log('EPG Fuzzy Match - Service handler started', level=xbmc.LOGINFO)

    while not monitor.abortRequested():
        if monitor.waitForAbort(0.5): break

        if not xbmc.getCondVisibility('Window.IsActive(%s)' % 'MyPVRGuide.xml'):
            no_match()
            win.setProperty("Fuzzy.cache_id", "")
            xbmc.sleep(1000)

        elif win.getProperty('Fuzzy.status') == 'busy':
            xbmc.sleep(100)

        elif xbmc.getInfoLabel("ListItem.EpgEventTitle") != win.getProperty('Fuzzy.epgtitle'):
            no_match()
            win.setProperty("Fuzzy.epgtitle", xbmc.getInfoLabel("ListItem.EpgEventTitle"))
            xbmc.sleep(100)

        else:
            # call service
            win.setProperty("Fuzzy.status", "busy")
            monitorgui()
            win.setProperty("Fuzzy.status", "")

    xbmc.log('EPG Fuzzy Match - Service handler ended', level=xbmc.LOGINFO)