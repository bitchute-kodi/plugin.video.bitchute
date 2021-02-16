<?xml version="1.0" encoding="UTF-8"?>
<addon id="plugin.video.bitchute"
version="0.0.1"
name="BitChute(alpha)"
provider-name="jasonfrancis">
<requires>
  <import addon="xbmc.python" version="3.0.0"/>
  <import addon="script.module.requests" version="2.12.4"/>
  <import addon="script.module.beautifulsoup4" version="4.5.3"/>
  <import addon="script.module.future" version="0.17.1" />
</requires>
<extension point="xbmc.python.pluginsource" library="main.py">
  <provides>video</provides>
</extension>
<extension point="xbmc.addon.metadata">
  <summary lang="en">BitChute Plugin for Kodi using WebTorrent.</summary>
  <description lang="en">A plugin for streaming videos from BitChute.</description>
  <disclaimer lang="en">THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED</disclaimer>
</extension>
</addon>
