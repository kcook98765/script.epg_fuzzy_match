import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import re, sys, os, time, re
import simplecache
import urllib, urllib.parse
import json
import datetime

dialog = xbmcgui.Dialog()
win = xbmcgui.Window(10000)
_cache = simplecache.SimpleCache()

# TODO, use md5 hashing for DB keys :  https://www.geeksforgeeks.org/md5-hash-python/

def disp_notification(type):
    addon = xbmcaddon.Addon("script.epg_fuzzy_match")
    notification_enabled = addon.getSetting('notification_enabled')
    if notification_enabled == 'false':
       return ''

    if type == 'Multi':
       message = 'Found Multiple Matches'
    elif type == 'Single':
        message = 'Found Single Match'
    else:
        return ''

    dialog.notification('EPG Match', message, xbmcgui.NOTIFICATION_INFO, 100)

def debug_log(message):
    addon = xbmcaddon.Addon("script.epg_fuzzy_match")
    debug_enabled = addon.getSetting('debug_enabled')
    if debug_enabled == 'false':
        return ''
    
    debug = 'EPG Fuzzy Match: ' + message
    xbmc.log(debug, level=xbmc.LOGINFO)

def monitorgui():

    addon = xbmcaddon.Addon("script.epg_fuzzy_match")
    debug_enabled = addon.getSetting('debug_enabled')

    # gather all the pieces to uniquely identify 
    # the current item highlighted in guide
    
    imdb_id = xbmc.getInfoLabel("ListItem.IMDBNumber")
    
    # Use SHS imdbnumber if PVR data does not have it, but check year match, as sometimes get mismatch
    if imdb_id == '':
        if win.getProperty('SkinHelper.ListItem.Year') == xbmc.getInfoLabel("ListItem.Year"):
            imdb_id = win.getProperty('SkinHelper.ListItem.Imdbnumber')
  
    
    d = {
        "title" : xbmc.getInfoLabel("ListItem.EpgEventTitle"),
        "imdbnumber" : imdb_id,
        "year" : xbmc.getInfoLabel("ListItem.Year"),
        "season" : xbmc.getInfoLabel("ListItem.Season"),
        "episode" : xbmc.getInfoLabel("ListItem.Episode"),
        "rel_date" : xbmc.getInfoLabel("ListItem.ReleaseDate"),
        "org_date" : xbmc.getInfoLabel("ListItem.OriginalDate"),
        "prem_date" : xbmc.getInfoLabel("ListItem.Premiered"),
        "ep_name" : xbmc.getInfoLabel("ListItem.EpisodeName"),
        "status" : xbmc.getInfoLabel("ListItem.Status"),
        "cast" : xbmc.getInfoLabel("ListItem.Cast")
    }
    
    
    if not d['season']:
        d['season'] = -1

    if not d['episode']:
        d['episode'] = -1
            
    # build cache id
    this_cache_id = 'EPG_Match19'
    for x in d:
        this_cache_id = this_cache_id + '|' + str(d[x])
    
    # if it matches current processed data, then just return
    if win.getProperty('Fuzzy.cache_id') == this_cache_id:
        return
       
    # starting a new lookup, set new cache property
    win.setProperty("Fuzzy.cache_id", this_cache_id)
    
    # check if data is already cached
    mycache = _cache.get(this_cache_id)
    
    if mycache and debug_enabled == 'false':
       # cache data exists (and debug not enabled), set properties and return
       
       win.setProperty("Fuzzy.context", mycache[0])
       win.setProperty("Fuzzy.label", mycache[1])
       win.setProperty("Fuzzy.xsp", mycache[2])
       set_cache(this_cache_id)
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
        set_cache(this_cache_id)
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
        set_cache(this_cache_id)
    return

def set_cache(this_cache_id):
    mycache = []
    mycache.append(win.getProperty('Fuzzy.context'))
    mycache.append(win.getProperty('Fuzzy.label'))
    mycache.append(win.getProperty('Fuzzy.xsp'))
    debug = 'cache_store: %s' % (mycache)
    debug_log(debug)
    _cache.set( this_cache_id, mycache, expiration=datetime.timedelta(days=1))
    return

def no_match():
    win.setProperty("Fuzzy.context", "")
    win.setProperty("Fuzzy.xsp", "")
    win.setProperty("Fuzzy.label", "")
    return

def clean_string(s):
    out = re.sub("[^0-9a-zA-Z]+", " ", s)
    out = re.sub(" {2}", " ", out)
    out = out.lower()

#    debug = 'Title Cleaned: ' + out
#    debug_log(debug)
    
    return out

def search_series(cache_id, **kwargs):
    search_title = kwargs.get('title')
    search_imdbnumber = kwargs.get('imdbnumber')
    search_episode_title = kwargs.get('ep_name')
    search_season = kwargs.get('season')
    search_episode = kwargs.get('episode')
    search_rel_date = kwargs.get('rel_date')
    search_prem_date = kwargs.get('prem_date')
    
    
    fix_date = re.split("\/", search_prem_date)
    y = len(fix_date)
    if y == 3:
        search_prem_date = fix_date[2] + '-' + fix_date[0] + '-' + fix_date[1]

    fix_date = re.split("\/", search_rel_date)
    y = len(fix_date)
    if y == 3:
        search_rel_date = fix_date[2] + '-' + fix_date[0] + '-' + fix_date[1]

    debug = 'Initial epg data for series: title %s, imdb: %s ep_title: %s season: %s episode: %s rel_date: %s, prem_date %s' % (search_title, search_imdbnumber, search_episode_title, search_season, search_episode, search_rel_date, search_prem_date)
    debug_log(debug)


    
    ct_title = clean_string(search_title)

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
        
        
        cr_title = clean_string(result['result']['tvshows'][i]['title'])
        
        cr_alt_title = re.sub("and ", "", cr_title)


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
        elif result['result']['tvshows'][i]['premiered'] == search_prem_date and match_type != 'imdb' and match_type != 'title':
            tvshowid = result['result']['tvshows'][i]['tvshowid']
            match_type = 'premiered'
        elif ct_title == cr_title and match_type != 'imdb' and match_type != 'title' and match_type != 'premiered':
            tvshowid = result['result']['tvshows'][i]['tvshowid']
            match_type = 'fuzzy'
        elif ct_title == cr_alt_title and match_type != 'imdb' and match_type != 'title' and match_type != 'premiered':
            tvshowid = result['result']['tvshows'][i]['tvshowid']
            match_type = 'fuzzy_alt'
        else:
            debug = 'Raw Series data not matched IMDB: %s Title: %s Premiered: %s cr_title: %s cr_alt_title: %s ct_title: %s' % (result['result']['tvshows'][i]['imdbnumber'],result['result']['tvshows'][i]['title'], result['result']['tvshows'][i]['premiered'], cr_title, cr_alt_title, ct_title)
            debug_log(debug)

    if match_type == 'None' or tvshowid == '':
        debug = 'Raw Series match not found IMDB: %s Title: %s Premiered: %s' % (search_imdbnumber, search_title, search_prem_date)
        debug_log(debug)
        no_match()
        return ''

    debug = 'Found a match for series via %s , tvshowid: %s' % (match_type, tvshowid)
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
    
    cr_title = clean_string(search_episode_title)
    
    for i in range(0, result['result']['limits']['total']):

        ct_title = clean_string(result['result']['episodes'][i]['originaltitle'])
        
        if int(result['result']['episodes'][i]['season']) == int(search_season) and int(result['result']['episodes'][i]['episode']) == int(search_episode) and match_type == 'None':
            # SE match
            files.append(result['result']['episodes'][i]['file'])
            match_type = 'SE'
            debug = 'Raw episode data match %s : %s %s - %s %s' % (match_type, search_season, search_episode, result['result']['episodes'][i]['season'], result['result']['episodes'][i]['episode'])
            debug_log(debug)
            
        elif result['result']['episodes'][i]['originaltitle'] == search_episode_title:
            # exact title match, only display this one
            files = [result['result']['episodes'][i]['file']]
            match_type = 'title'
            debug = 'Raw episode data match %s : %s - %s' % (match_type, search_episode_title, result['result']['episodes'][i]['originaltitle'])
            debug_log(debug)
            break
            
        elif result['result']['episodes'][i]['firstaired'] == search_rel_date and result['result']['episodes'][i]['firstaired'] != '':
            files.append(result['result']['episodes'][i]['file'])
            match_type = 'airdate'
            debug = 'Raw episode data match %s : %s - %s' % (match_type, search_rel_date, result['result']['episodes'][i]['firstaired'])
            debug_log(debug)
            
        elif ct_title == cr_title:
            files = [result['result']['episodes'][i]['file']]
            match_type = 'fuzzy'           
            debug = 'Raw episode data match %s : %s - %s' % (match_type, ct_title, cr_title)
            debug_log(debug)
            break
        else:
            debug = 'Raw episode data not matched S: %s E: %s Title: %s Firstair: %s' % (result['result']['episodes'][i]['season'], result['result']['episodes'][i]['episode'], result['result']['episodes'][i]['originaltitle'], result['result']['episodes'][i]['firstaired'])
            debug_log(debug)

    if len(files) > 0:
        
        
        debug = 'Found a match for episode via %s ' % (match_type)
        debug_log(debug)
      
        xsp = '{"rules":{"or":['


        for i in range(0, len(files)):
            if i > 0:
                xsp = xsp + ","
            xsp = xsp + '{"field":"filename","operator":"is","value":"%s"}' % (files[i])
            file_path = files[i]

        xsp = xsp + ']},"type":"episodes"}'

        xsp = 'Videos,videodb://tvshows/titles/-1/-1/-1/-1/?xsp=' + urllib.parse.quote_plus(xsp)

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
    debug = 'Raw Episode match not found S: %s E: %s Title: %s Firstair: %s' % (search_season, search_episode, search_episode_title, search_prem_date)
    debug_log(debug)
    no_match()


def search_movies(cache_id, **kwargs):
    # sometimes PVR title may include year,
    # if so, "clean" the title and grab that year
    # in case actual Year field empty or different
    
    search_raw = kwargs.get('title')
    search_year = kwargs.get('year')
    search_imdbnumber = kwargs.get('imdbnumber')
    search_cast = kwargs.get('cast')
    
    debug = 'Cast Raw: %s' % (search_cast)
    debug_log(debug)
    
    debug = 'Cast Split '
    y = re.split("\n", search_cast)
    for i in range(0, len(y)):
        debug = debug + ':' + y[i]
    debug_log(debug)
    
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

        xsp = 'Videos,videodb://movies/titles/?xsp=' + urllib.parse.quote_plus(xsp)

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

    min_year = int(search_year) - 5
    max_year = int(search_year) + 5
    
    ct_movie = clean_string(search_movie)

    search_movie_parts = re.split(" ", ct_movie)

    search_cast = kwargs.get('cast')
    y = re.split("\n", search_cast)
    
    title_filter = ''
    alt_title_filter = ''
    do_or = ''

    for part in search_movie_parts:
        if title_filter != '':
            title_filter = title_filter + ','

        title_filter = title_filter + '{"field": "title", "operator": "contains", "value": "' + part + '"}'

        if alt_title_filter != '':
            alt_title_filter = alt_title_filter + ','
            
        alt_part = part
            
        if part == '0':
            alt_part = 'zero'
        elif part == '1':
            alt_part = 'one'
        elif part == '2':
            alt_part = 'two'
        elif part == '3':
            alt_part = 'three'
        elif part == '4':
            alt_part = 'four'
        elif part == '5':
            alt_part = 'five'
        elif part == '6':
            alt_part = 'six'
        elif part == '7':
            alt_part = 'seven'
        elif part == '8':
            alt_part = 'eight'
        elif part == '9':
            alt_part = 'nine'
        elif part == '10':
            alt_part = 'ten'
        elif part == 'zero':
            alt_part = '0'
        elif part == 'one':
            alt_part = '1'
        elif part == 'two':
            alt_part = '2'
        elif part == 'three':
            alt_part = '3'
        elif part == 'four':
            alt_part = '4'
        elif part == 'five':
            alt_part = '5'
        elif part == 'six':
            alt_part = '6'
        elif part == 'seven':
            alt_part = '7'
        elif part == 'eight':
            alt_part = '8'
        elif part == 'nine':
            alt_part = '9'
        elif part == 'ten':
            alt_part = '10'

        if part != alt_part:
            do_or = 1

        alt_title_filter = alt_title_filter + '{"field": "title", "operator": "contains", "value": "' + alt_part + '"}'

    if do_or == 1:
        command = '{"jsonrpc": "2.0", ' \
            '"method": "VideoLibrary.GetMovies", ' \
            '"params": { ' \
            '"filter": { "or" : [{"and": [%s]},{"and": [%s]}] }, ' \
            '"sort": { "order": "ascending", "method": "label" }, ' \
            '"properties": ["title", "imdbnumber", "year", "file", "cast"] ' \
            '}, "id": 1}' % (title_filter, alt_title_filter)        
    else:
        command = '{"jsonrpc": "2.0", ' \
            '"method": "VideoLibrary.GetMovies", ' \
            '"params": { ' \
            '"filter": { "and": [ %s ]}, ' \
            '"sort": { "order": "ascending", "method": "label" }, ' \
            '"properties": ["title", "imdbnumber", "year", "file", "cast"] ' \
            '}, "id": 1}' % (title_filter)

    debug = 'JSON sent: ' + command
    debug_log(debug)

    result = json.loads(xbmc.executeJSONRPC(command))
    matches = result['result']['limits']['total']
    files = []
    match_type = 'None'
    
    for i in range(0, result['result']['limits']['total']):
        
        cr_movie = clean_string(result['result']['movies'][i]['title'])

        debug = 'Checking for movie match : %s vs lookup: %s' % (ct_movie, cr_movie)
        debug_log(debug)

        cast_match_count = 0
        for c in range(0,len(result['result']['movies'][i]['cast'])):
            for d in range(0, len(y)):
                if result['result']['movies'][i]['cast'][c]['name'] == y[d]:
                    cast_match_count = cast_match_count + 1
            
        debug = 'Cast Match Count: %s' % (cast_match_count)
        debug_log(debug)

        
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
                files = [result['result']['movies'][i]['file']]
                match_type = 'title-fuzzy_year'
                break
        elif ct_movie == cr_movie:
            # cleaned title match
            if result['result']['movies'][i]['year'] == search_year:
                files = [result['result']['movies'][i]['file']]
                match_type = 'fuzzy_title-year'
                break
            elif result['result']['movies'][i]['year'] > min_year \
                and result['result']['movies'][i]['year'] < max_year:
                # year +/- limits, so add to list and don't break
                files = [result['result']['movies'][i]['file']]
                match_type = 'fuzzy_title-fuzzy_year'
                break
        elif cast_match_count == len(y) and match_type == 'None':
                files.append(result['result']['movies'][i]['file'])
                match_type = 'cast_match'
        else:
            debug = 'Raw movie not a match: imdb: %s , title: %s, year: %s' % (result['result']['movies'][i]['imdbnumber'], result['result']['movies'][i]['title'], result['result']['movies'][i]['year'])
            debug_log(debug)

    # completed search, act on results
    
    if match_type == 'None':
        debug = 'No match found via imdb: %s , title: %s, year: %s, min_year: %s, max_year: %s' % (search_imdbnumber, search_movie, search_year, min_year, max_year)
        debug_log(debug)
    else:
        debug = 'Found a match via %s , movie: %s' % (match_type, search_movie)
        debug_log(debug)
    
    match_return = [match_type, files]

    return match_return




if __name__ == '__main__':

    monitor = xbmc.Monitor()
    xbmc.log('EPG Fuzzy Match - Service handler started', level=xbmc.LOGINFO)

    while not monitor.abortRequested():
        if monitor.waitForAbort(0.5): break

        if not xbmc.getCondVisibility('Window.IsActive(%s)' % 'MyPVRGuide.xml') and not xbmc.getCondVisibility('Window.IsActive(%s)' % 'MyPVRChannels.xml'):
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