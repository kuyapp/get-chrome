Get Chrome Installer
--------------------
[![Build Status]][Travis CI]

A heroku app that get latest Chrome installer URLs.

###Examples

Get stable channel:

http://get-chrome.herokuapp.com/channel/stable

Get beta channel:

http://get-chrome.herokuapp.com/channel/beta

Get dev channel:

http://get-chrome.herokuapp.com/channel/dev

Get all channel:

http://get-chrome.herokuapp.com/channel/all

###How to use
```
@echo off
start "chrome" "%~dp0Chrome-Bin\chrome.exe" --no-first-run --disable-plugins-discovery --extra-plugin-dir="%~dp0Plugins" --User-data-dir="%~dp0Data" --disk-cache-dir="%USERPROFILE%\ChromeCache" --disable-directwrite-for-ui
@echo on
```

[Build Status]: https://img.shields.io/travis/kuyapp/get-chrome/master.svg?style=flat
[Travis CI]:    https://travis-ci.org/kuyapp/get-chrome
