# update:
Add settings for this service, to enable/disable notifications (Context "Math" entry will still be inserted for match(es), just no notification popups.


# script.epg_fuzzy_match
 Kodi EPG Fuzzy match to local library
 
 This is a simple service that requires no skin specific changes to use.
 
 When you are in the PVR Guide and focus on a Movie, this service automatically looks for a matching movie in your local library using some "fuzzy" matching (IE year can be +/- 1 year to account for possible EPG year being different than local library year.
 
 If a match, or matches are found, then you'll see a brief notification appear calling out the match(es).
 
 Also, you will get an extra context menu entry (only in EPG Guide view) with either:
 
 "Library Match" , which when used puts you into the Movie Information page
 or
 "Library Matches", which then populates a list view of the matching movies.
 
 This is alpha right now, but I am using it with a local Movie DB of apx 4,500 movies and with a PVR (channelsDVR) backend with 300+ channels.
 
 It seems to work for what I wanted.
 
 TODO:
 
 apply to TV Series (though this will require some work as local vs pvr may use different entities to set season and episode numbers)
 
 Add optional skin Properties (so skinners could display related match data directly in skin)
 
 Code cleanup and optimizations (though already using simplecache to reduce JSON calls for entry matching).
