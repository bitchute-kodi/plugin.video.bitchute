# -*- coding: utf-8 -*-
# Module: default
# Author: Jason Francis
# Created on: 2017-10-15
# Based on plugin.video.example(https://github.com/romanvm/plugin.video.example)
# License: MIT https://opensource.org/licenses/MIT

import sys
from urlparse import parse_qsl
import xbmcgui
import xbmcplugin
import xbmcaddon
import re
import requests
import json
import time
from bs4 import BeautifulSoup
import subprocess

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]
# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])
baseUrl = "https://www.bitchute.com"
addon = xbmcaddon.Addon()

class VideoLink:
    def __init__(self, containerSoup):
        titleDiv = containerSoup.findAll('div', "channel-videos-title")[0]
        linkSoup = titleDiv.findAll('a')[0]
        
        self.title = linkSoup.string
        self.pageUrl = linkSoup.get("href")
        self.id = self.pageUrl.split("/")[-1]
        self.thumbnail = None
        self.url = None
        #before we can find thumnails let's strip out play button images.
        for playButton in containerSoup.findAll('img', "play-overlay-icon"):
            playButton.extract()
        
        thumbnailMatches = containerSoup.findAll('img', "img-responsive")
        
        if thumbnailMatches:
            self.thumbnail = baseUrl + thumbnailMatches[0].get("data-src")

    @staticmethod
    def getUrl(channelId, videoId):
        req = fetchLoggedIn(baseUrl + "/video/" + videoId)
        soup = BeautifulSoup(req.text, 'html.parser')
        for container in soup.findAll("span", {"class":"video-magnet"}):
            for link in container.findAll("a"):
                magnetUrl = link.get("href")
                if magnetUrl.startswith("magnet:?"):
                    return magnetUrl
        # If we couldn't find the magnet URL return the default .torrent file.
        return(baseUrl + "/torrent/" + channelId + "/" + videoId + ".torrent")
    def setUrl(self, channelId):
        self.url = self.getUrl(channelId, videoId)

class Channel:
    def __init__(self, channelName, pageNumber = None):
        self.channelName = channelName
        self.videos = []
        self.thumbnail = None
        self.page = 1
        if pageNumber is not None:
            self.page = pageNumber
        self.hasPrevPage = False
        self.hasNextPage = False

        self.setThumbnail()
        self.setPage(self.page)
	
    def setThumbnail(self):
        thumbnailReq = fetchLoggedIn(baseUrl + "/channel/" + self.channelName)
        thumbnailSoup = BeautifulSoup(thumbnailReq.text, 'html.parser')
        thumbnailImages = thumbnailSoup.findAll("img", id="fileupload-medium-icon-2")
        if thumbnailImages and thumbnailImages[0].has_attr("data-src"):
            self.thumbnail = baseUrl + thumbnailImages[0].get("data-src")

    def setPage(self, pageNumber):
        self.videos = []
        self.page = pageNumber
        self.hasPrevPage = False
        self.hasNextPage = False
        
        r = postLoggedIn(baseUrl + "/channel/" + self.channelName + "/extend/", baseUrl + "/channel/" + self.channelName + "/",{"offset": 10 * (self.page - 1)})
        soup = BeautifulSoup(r.text, 'html.parser')

        for videoContainer in soup.findAll('div', "channel-videos-container"):
            self.videos.append(VideoLink(videoContainer))

        if len(self.videos) >= 10:
            self.hasNextPage = True
        
        # for now I only know how to find the channel's ID from a video, so take the last item
        # in videos and find the channel's ID.
        videoRequest = requests.get(baseUrl + self.videos[-1].pageUrl)
        channelIdMatches = re.search('/torrent/\d+', videoRequest.text)
        if channelIdMatches:
            self.id = channelIdMatches.group().split("/")[-1]
        else:
            raise ValueError("channel Id not found for " + self.channelName + ".")

class MyPlayer(xbmc.Player):
    def __init__(self):
        MyPlayer.is_active = True
        print("#MyPlayer#")
    
    def onPlayBackPaused( self ):
        xbmc.log("#Im paused#")
        
    def onPlayBackResumed( self ):
        xbmc.log("#Im Resumed #")
        
    def onPlayBackStarted( self ):
        print("#Playback Started#")
        try:
            print("#Im playing :: " + self.getPlayingFile())
        except:
            print("#I failed get what Im playing#")
            
    def onPlayBackEnded( self ):
        print("#Playback Ended#")
        self.is_active = False
        
    def onPlayBackStopped( self ):
        print("## Playback Stopped ##")
        self.is_active = False
    
    def sleep(self, s):
        xbmc.sleep(s) 
def login():
    #BitChute uses a token to prevent csrf attacks, get the token to make our request.
    r = requests.get(baseUrl)
    csrfJar = r.cookies
    soup = BeautifulSoup(r.text, 'html.parser')
    csrftoken = soup.findAll("input", {"name":"csrfmiddlewaretoken"})[0].get("value")

    #Fetch the user info from settings
    username = xbmcplugin.getSetting(_handle, 'username')
    password = xbmcplugin.getSetting(_handle, 'password')
    post_data = {'csrfmiddlewaretoken': csrftoken, 'username': username, 'password': password}
    headers = {'Referer': baseUrl + "/", 'Origin': baseUrl}
    response = requests.post(baseUrl + "/accounts/login/", data=post_data, headers=headers, cookies=csrfJar)
    authCookies = []
    for cookie in response.cookies:
        authCookies.append({ 'name': cookie.name, 'value': cookie.value, 'domain': cookie.domain, 'path': cookie.path, 'expires': cookie.expires })
    
    #stash our cookies in our JSON cookie jar
    cookiesJson = json.dumps(authCookies)
    addon.setSetting(id='cookies', value=cookiesJson)

    return(authCookies)
    
def getSessionCookie():
    cookiesString = xbmcplugin.getSetting(_handle, 'cookies')
    if cookiesString:
        cookies = json.loads(cookiesString)
    else:
        cookies = login()
    
    #If our cookies have expired we'll need to get new ones.
    now = int(time.time())
    for cookie in cookies:
        if now >= cookie['expires']:
            cookies = login()
            break
    
    jar = requests.cookies.RequestsCookieJar()
    for cookie in cookies:
        jar.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie['path'], expires=cookie['expires'])
    
    return jar

def fetchLoggedIn(url):
    req = requests.get(url, cookies=sessionCookies)
    soup = BeautifulSoup(req.text, 'html.parser')
    loginUser = soup.findAll("ul", {"class":"user-menu-dropdown"})
    if loginUser:
        profileLink = loginUser[0].findAll("a",{"class":"dropdown-item", "href":"/profile"})
        if profileLink:
            return req
    #Our cookies have gone stale, clear them out.
    xbmcplugin.setSetting(_handle, id='cookies', value='')
    raise ValueError("Not currently logged in.")

def postLoggedIn(url, referer, params):
	#BitChute uses a token to prevent csrf attacks, get the token to make our request.
	csrftoken = None
	for cookie in sessionCookies:
		if cookie.name == 'csrftoken':
			csrftoken = cookie.value
			break

	post_data = {'csrfmiddlewaretoken': csrftoken}
	for param in params:
		post_data[param] = params[param]

	headers = {'Referer': referer, 'Host': 'www.bitchute.com', 'Origin': baseUrl, 'Pragma': 'no-cache', 'Cache-Control': 'no-cache'}
	response = requests.post(url, data=post_data, headers=headers, cookies=sessionCookies)
	return response

def getSubscriptions():
    subscriptions = []
    req = fetchLoggedIn(baseUrl + "/subscriptions")
    soup = BeautifulSoup(req.text, 'html.parser')
    for container in soup.findAll("div", {"class":"subscription-container"}):
        for link in container.findAll("a", {"rel":"author"}):
            name = link.get("href").split("/")[-1]
            subscriptions.append(Channel(name))
    return(subscriptions)

sessionCookies = getSessionCookie()



def getCategories():
    """
    Get the list of video categories.
    Here you can insert some parsing code that retrieves
    the list of video categories (e.g. 'Movies', 'TV-shows', 'Documentaries' etc.)
    from some site or server.
    :return: list
    """
    categories = getSubscriptions()
    return categories


def getVideos(categoryName):
    """
    Get the list of videofiles/streams.
    Here you can insert some parsing code that retrieves
    the list of videostreams in a given category from some site or server.
    :param category: str
    :return: list
    """
    category = Channel(categoryName)
    return category.videos


def listCategories():
    """
    Create the list of video categories in the Kodi interface.
    :return: None
    """
    # Get video categories
    categories = getCategories()
    # Create a list for our items.
    listing = []
    # Iterate through categories
    for category in categories:
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=category.channelName, thumbnailImage=category.thumbnail)
        # Set a fanart image for the list item.
        # Here we use the same image as the thumbnail for simplicity's sake.
        list_item.setProperty('fanart_image', category.thumbnail)
        # Set additional info for the list item.
        # Here we use a category name for both properties for for simplicity's sake.
        # setInfo allows to set various information for an item.
        # For available properties see the following link:
        # http://mirrors.xbmc.org/docs/python-docs/15.x-isengard/xbmcgui.html#ListItem-setInfo
        list_item.setInfo('video', {'title': category.channelName, 'genre': category.channelName})
        # Create a URL for the plugin recursive callback.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = '{0}?action=listing&category={1}'.format(_url, category.channelName)
        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True
        # Add our item to the listing as a 3-element tuple.
        listing.append((url, list_item, is_folder))
    # Add our listing to Kodi.
    # Large lists and/or slower systems benefit from adding all items at once via addDirectoryItems
    # instead of adding one by ove via addDirectoryItem.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def listVideos(categoryName, pageNumber = None):
    """
    Create the list of playable videos in the Kodi interface.
    :param category: str
    :return: None
    """
    if pageNumber is None:
        pageNumber = 1
    # Get the list of videos in the category.
    category = Channel(categoryName, pageNumber)
    videos = category.videos
    # Create a list for our items.
    listing = []
    # Iterate through videos.
    for video in videos:
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=video.title, thumbnailImage=video.thumbnail)
        # Set a fanart image for the list item.
        # Here we use the same image as the thumbnail for simplicity's sake.
        list_item.setProperty('fanart_image', video.thumbnail)
        # Set additional info for the list item.
        list_item.setInfo('video', {'title': video.title, 'genre': video.title})
        # Set additional graphics (banner, poster, landscape etc.) for the list item.
        # Again, here we use the same image as the thumbnail for simplicity's sake.
        list_item.setArt({'landscape': video.thumbnail})
        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')
        # Create a URL for the plugin recursive callback.
        # Example: plugin://plugin.video.example/?action=play&video=http://www.vidsplay.com/vids/crab.mp4
        url = '{0}?action=play&videoId={1}&channelId={2}'.format(_url, video.id, category.id)
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False
        # Add our item to the listing as a 3-element tuple.
        listing.append((url, list_item, is_folder))
    # If the category has a next page add it to our listing.
    if category.hasNextPage:
        list_item = xbmcgui.ListItem(label="Next Page...")
        url = '{0}?action=listing&category={1}&page={2}'.format(_url, category.channelName, category.page + 1)
        listing.append((url, list_item, True))

    # Add our listing to Kodi.
    # Large lists and/or slower systems benefit from adding all items at once via addDirectoryItems
    # instead of adding one by ove via addDirectoryItem.
    xbmcplugin.addDirectoryItems(_handle, listing, len(listing))
    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_UNSORTED)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)


def playVideo(channelId, videoId):
    print(videoId)
    videoUrl = VideoLink.getUrl(channelId, videoId)
    playing = 0
    # start webtorrent fetching path
    output = ""
    cnt = 0
    dlnaUrl = None
    webTorrentClient = subprocess.Popen('webtorrent-hybrid "' +  videoUrl + '" --dlna', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print("running with PID " + str(webTorrentClient.pid))
    for stdout_line in webTorrentClient.stdout:
        output += stdout_line.decode()
        cnt += 1
        if cnt > 10:
            break

    dlnaMatches = re.search('http:\/\/((\w|\d)+(\.)*)+:\d+\/\d+', output)
    if dlnaMatches:
        dlnaUrl = dlnaMatches.group()
    else:
        webTorrentClient.terminate()
        raise ValueError("could not determine the dlna URL.")

    print("Streaming at: " + dlnaUrl)

    while webTorrentClient.poll() == None:
        if playing == 0:
            playing = 1
            playWithCustomPlayer(dlnaUrl, webTorrentClient)

def playWithCustomPlayer(url, webTorrentClient):
    play_item = xbmcgui.ListItem(path=url)
    # Get an instance of xbmc.Player to work with.
    player = MyPlayer()
    player.play( url, play_item )
    xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)
    
    while player.is_active:
        player.sleep(100)

    webTorrentClient.terminate()
    

def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring
    :param paramstring:
    :return:
    """
    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))
    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            listVideos(params['category'], int(params.get('page', '1')))
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            playVideo(params['channelId'], params['videoId'])
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        listCategories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
