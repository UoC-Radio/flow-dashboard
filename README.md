# flow-dashboard [![Build Status](https://github.com/UoC-Radio/flow-dashboard/workflows/docker%20build/badge.svg)](https://github.com/UoC-Radio/flow-dashboard/actions?query=workflow%3A%22docker+build%22)
#### A GTK+ based GUI generator of the radio station's on-air schedule.

This is a graphical XML generator and database front-end application. It acts as the GUI of [Audio Scheduler](https://github.com/UoC-Radio/audio-scheduler/). It aims to:
* Facilitate creation of the [music schedule](http://radio.uoc.gr/schedule/schedule.xml), which is given as input to Audio Scheduler.
* Provide zone management for the music library of the radio station.

## Screenshots
[![Initial state](/gallery/thumbnails/initial_state_thumbnail.png?raw=true)](/gallery/initial_state.png?raw=true)
[![Menu options](/gallery/thumbnails/menu_thumbnail.png?raw=true)](/gallery/menu.png?raw=true)  
[![Import progress bar](/gallery/thumbnails/import_progress_thumbnail.png?raw=true)](/gallery/import_progress.png?raw=true)
[![After import](/gallery/thumbnails/imported_thumbnail.png?raw=true)](/gallery/imported.png?raw=true)

## Build and Run natively
### Dependencies
To run flow-dashboard, you will need to have the following installed:
* Python 3
* GTK+3 [[Instructions]](https://pygobject.readthedocs.io/en/latest/getting_started.html)
* lxml for python 3 [[Instructions]](https://lxml.de/installation.html)

### Run
After installing the dependencies above, just do:  
```
python3 ./src/main.py
```

## Build and Run with Docker
An alternative (and probably easier) way to build and run the app is by using Docker. Besides Docker, you don't need any other dependencies installed.

To build and run the app from source:
```
./build
./run
```

To download and run the latest version of the app:
```
./quick_run
```
The above command first updates the app if it is outdated, and then runs it.


The app will run locally as a web application.

## Credits
[ggalan87](https://github.com/ggalan87) for his advice on GUI design  
[looselyrigorous](https://github.com/looselyrigorous) for his CSS styling ideas
