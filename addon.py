import xbmc, xbmcgui, xbmcaddon, xbmcvfs
import re, sys, os, time, re
import simplecache
import urllib, urllib.parse
import json
import datetime

dialog = xbmcgui.Dialog()

win = xbmcgui.Window(10000)


# initiate the cache
_cache = simplecache.SimpleCache()

def monitorgui(current_item):
    
   x = re.split("~", current_item, 1)
   search_movie = x[0]
   search_year = x[1]

   if xbmc.getCondVisibility('Container(%s).Scrolling') % xbmcgui.getCurrentWindowId() or \
      win.getProperty('Fuzzy.status') == 'busy' or \
      not xbmc.getCondVisibility('Window.IsActive(%s)' % 'MyPVRGuide.xml'):
      win.setProperty("Fuzzy.context", "")
      win.setProperty("Fuzzy.xsp", "")
      xbmc.sleep(2000)
      return current_item
      
   this_item = ismovie(current_item)

#   debug = 'Fuzzy Match This loop: ' + this_item

#   xbmc.log(debug, level=xbmc.LOGINFO)

   
   if this_item != current_item:

      # check if cache used
      cache_id = 'EPG_Match.' + this_item
      mycache = _cache.get(cache_id)
      if mycache and this_item == '~':
         debug = 'EPG Fuzzy Match - cache_hit: %s' % (this_item)
         xbmc.log(debug, level=xbmc.LOGINFO)
         win.setProperty("Fuzzy.context", mycache[0])
         win.setProperty("Fuzzy.label", mycache[1])
         win.setProperty("Fuzzy.xsp", mycache[2])
         win.setProperty("Fuzzy.status", "")
         _cache.set( cache_id, mycache, expiration=datetime.timedelta(days=1))
         
         if mycache[0] == 'Muli':
             notify('Found multiple matches')
         elif mycache[0] == 'Single':
            notify('Found single match')
         return this_item
      
      search_result = lib_search(this_item)
      current_item = search_result[0]
      matches = search_result[1]
      
      search_movie = search_result[3]
      search_year = search_result[4]
      
      debug = 'EPG Fuzzy Match - search:  ' +  current_item +  ' : ' + str(matches) + ' : ' + search_movie + ' : ' + str(search_year)
      xbmc.log(debug, level=xbmc.LOGINFO)
      
      xsp = '{"rules":{"or":['
      
      # ~ joined list of files
      file_string = search_result[2]
      
      files = re.split("~", file_string)

      for i in range(0, len(files)):
         if i > 0:
            xsp = xsp + ","

         xsp = xsp + '{"field":"filename","operator":"is","value":"%s"}' % (files[i])
         
         file_path = files[i]

      xsp = xsp + ']},"type":"movies"}'

      xsp = urllib.parse.quote_plus(xsp)

      if matches > 1:
         # indicate multi matches, set context to send to list of matches, trigger notification of such
         notify('Found multiple matches')
         win.setProperty("Fuzzy.context", "Multi")
         win.setProperty("Fuzzy.xsp", xsp)
         
      elif matches == 1:
         # indicate 1 match, set context to go to dialogvideoinfo window, trigger notification of such
         notify('Found a single match')
         win.setProperty("Fuzzy.context", "Single")
         win.setProperty("Fuzzy.label",search_movie)
         win.setProperty("Fuzzy.xsp", file_path)
         
      else:
         # no matches, no context menu addition, trigger notification of no match(es) found
#         notify('No match found')
         win.setProperty("Fuzzy.context", "")
         win.setProperty("Fuzzy.xsp", "")

      if this_item != '~':
         mycache = (win.getProperty("Fuzzy.context"), win.getProperty("Fuzzy.label"), win.getProperty("Fuzzy.xsp"))
         cache_id = 'EPG_Match.' + this_item
         _cache.set( cache_id, mycache, expiration=datetime.timedelta(days=1))

   win.setProperty("Fuzzy.status", "free")
   current_item = this_item
   return current_item


def notify(message):
   dialog.notification('EPG Match', message, xbmcgui.NOTIFICATION_INFO, 100)

def ismovie(current_item):

   episode_num = xbmc.getInfoLabel("ListItem.Episode")
   season_num = xbmc.getInfoLabel("ListItem.Season")

   if episode_num == '':
       episode_num = -1
       
   if season_num == '':
       season_num = -1

   episode_num = int(episode_num)
   season_num = int(season_num)


   if episode_num >= 0 or season_num >= 0:
      current_item = '~'
      return current_item

   search_raw = xbmc.getInfoLabel("ListItem.EpgEventTitle")
   search_movie = ''
   search_year = ''
   x = re.split("\(", search_raw, 1)
   search_movie = str(x[0]).strip()
   y = len(x)

   if y == 2:
      y = re.split("\)", x[1], 1)
      y[0] = re.sub("[^0-9]+", "", y[0])
      if y[0] != '':
         search_year = int(y[0])

   if search_year == '':
      search_year = xbmc.getInfoLabel("ListItem.Year")

   if search_movie == '' or search_year == '':
      debug = 'EPG Fuzzy Match -  incomplete: ' + search_movie + 'x' + search_year
      xbmc.log(debug, level=xbmc.LOGINFO)
      current_item = '~'
      return current_item

   if current_item != '%s~%s' % (search_movie, search_year):
      win.setProperty("Fuzzy.status", "busy")
      win.setProperty("Fuzzy.match", "")
      win.setProperty("Fuzzy.match_count", "")
      return '%s~%s' % (search_movie, search_year)
   else:
      return current_item

def lib_search(this_item):

   x = re.split("~", this_item, 1)
   search_movie = x[0]
   
   if len(x) < 2:
      match_return = [this_item, 0, '', '', 0]
      return match_return
   
   if x[1] == '':
      match_return = [this_item, 0, '', '', 0]
      return match_return
   
   search_year = int(x[1])
   
   min_year = search_year - 2
   max_year = search_year + 2

   # todo: strip out odd charcters
   
   this_movie = re.sub("[^0-9a-zA-Z]+", " ", search_movie)
   this_movie = re.sub(" {2}", " ", this_movie)
   
   debug = 'EPG Fuzzy Match - split_movie: ' + this_movie
   xbmc.log(debug, level=xbmc.LOGINFO)

   search_movie_parts = re.split(" ", this_movie)
   
   y = len(search_movie_parts)
   last_index = y - 1
   
   if y == 1:
      title_filter = '{"field": "title", "operator": "is", "value": "' + search_movie_parts[0] + '"}'
   elif y == 2:
      title_filter = '{"field": "title", "operator": "startswith", "value": "' + search_movie_parts[0] + '"}'
      title_filter = title_filter + ',{"field": "title", "operator": "endswith", "value": "' + search_movie_parts[1] + '"}'
   else:
      title_filter = '{"field": "title", "operator": "startswith", "value": "' + search_movie_parts[0] + '"}'      
      
      title_filter = title_filter + ',{"field": "title", "operator": "endswith", "value": "' + search_movie_parts[last_index] + '"}'
      
      search_movie_parts.pop(last_index)
      search_movie_parts.pop(0)
      
      for part in search_movie_parts:
         title_filter = title_filter + ',{"field": "title", "operator": "contains", "value": "' + part + '"}'
   
   # add in the year range
   title_filter = title_filter + ',{"field": "year", "operator": "greaterthan", "value": "' + str(min_year) + '"}'
   title_filter = title_filter + ',{"field": "year", "operator": "lessthan", "value": "' + str(max_year) + '"}'

   command = '{"jsonrpc": "2.0", ' \
             '"method": "VideoLibrary.GetMovies", ' \
             '"params": { ' \
                '"filter": { "and": [ %s ]}, ' \
                '"sort": { "order": "ascending", "method": "label" }, ' \
                '"properties": ["title", "imdbnumber", "year", "file"] ' \
                '}, "id": 1}' % (title_filter)

   debug = 'EPG Fuzzy Match - JSON: ' + command

   xbmc.log(debug, level=xbmc.LOGINFO)
   result = json.loads(xbmc.executeJSONRPC(command))
   matches = result['result']['limits']['total']
   
   files = ''
   for i in range(0, result['result']['limits']['total']):
      if files == '':
         files = result['result']['movies'][i]['file']
      else:
         files = files + '~' + result['result']['movies'][i]['file']
   match_return = [this_item, matches, files, search_movie, search_year]
 
   return match_return
 


if __name__ == '__main__':

    current_item = '~'

    monitor = xbmc.Monitor()
    xbmc.log('EPG Fuzzy Match - Service handler started', level=xbmc.LOGINFO)

    while not monitor.abortRequested():
        if monitor.waitForAbort(0.5): break

        # call service
        current_item = monitorgui(current_item)

    xbmc.log('EPG Fuzzy Match - Service handler ended', level=xbmc.LOGINFO)