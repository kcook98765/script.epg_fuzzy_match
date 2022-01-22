import xbmc, xbmcgui
import sys

if __name__ == '__main__':
    if len(sys.argv) > 1:
        
        win = xbmcgui.Window(10000)
        windowID = xbmcgui.getCurrentWindowId()
        currwin = xbmcgui.Window(windowID) 
    
        xsp = win.getProperty("Fuzzy.xsp")
        label = win.getProperty("Fuzzy.label")
    
        if sys.argv[1] == "Single":
            xbmc.executebuiltin('Dialog.Close(all,true)')
            li = xbmcgui.ListItem(label)
            li.setInfo('video', {})
            li.setPath(xsp)
            currwin.close()
            dialog = xbmcgui.Dialog(li)
            dialog.info(li)
        elif sys.argv[1] == "Multi":
            xbmc.executebuiltin('Dialog.Close(all,true)')
            xbmc.executebuiltin('ActivateWindow(%s,return)' % (xsp))
 