"""
The Model

Copyright (C) 2018 Elias Papavasileiou <eliaspap@protonmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from gi.repository.Gtk import ListStore, SortType, TreePath
from helpers import Playlist, getPlaylistNameFromPath


class Model:
    """ Holds the application's data, as well as operations on them.

    The Model consists of four sub-models that correspond to the four main window parts:
    Flow Schedule, Zones, Zone Inspector and Playlists.
    """

    def __init__(self):
        """ Initialize sub-models.

        Do not initialize the zoneInspector sub-model,
        because no zone exists on application startup.
        """
        # Weekly Schedule Model
        self.schedule = {}
        for dayIndex in range(7):
            self.schedule[dayIndex] = ListStore(str, str)
            self.schedule[dayIndex].set_sort_column_id(0, SortType.ASCENDING)

        # Zone Model
        self.zones = ListStore(str, str, str, str)
        self.zones.set_sort_column_id(0, SortType.ASCENDING)

        # Zone Inspector Model
        self.zoneInspector = {}

        # Playlist Model
        self.playlists = ListStore(str, str)
        self.playlists.set_sort_column_id(0, SortType.ASCENDING)


    # Public methods

    def addZoneToDatabase(self, zoneName, zoneMaintainers='',
                          zoneDescription='', zoneComments=''):
        """ Add a zone to the database.

        Subsequently, initialize its inspector.
        """
        self.zones.append((zoneName, zoneDescription, zoneMaintainers, zoneComments))
        self.initZoneInspector(zoneName)

    def removeZoneFromDatabase(self, zoneRow):
        """
        Remove a zone from the database.

        Subsequently, remove every occurrence of it in the Flow Schedule.
        Also remove its inspector.
        """
        zoneName = self.zones[zoneRow][0]
        del self.zones[zoneRow]
        for dayIndex in range(7):
            while True:
                scheduleRow = self.getRowOfItemInColumnOfModel(zoneName, 1,
                                                               self.schedule[dayIndex])
                if scheduleRow is not None:
                    del self.schedule[dayIndex][scheduleRow]
                else:
                    break
        self.zoneInspector[zoneName].clear()
        del self.zoneInspector[zoneName]

    def editZoneNameInDatabase(self, oldZoneName, newZoneName):
        """ Edit a zone's name in the database.

        Subsequently, rename every occurrence of it in the Flow Schedule.
        Also rename its inspector.
        """
        zoneRow = self.getZoneRow(oldZoneName)
        self.zones[zoneRow][0] = newZoneName
        for dayIndex in range(7):
            while True:
                scheduleRow = self.getRowOfItemInColumnOfModel(oldZoneName, 1,
                                                               self.schedule[dayIndex])
                if scheduleRow is not None:
                    self.schedule[dayIndex][scheduleRow][1] = newZoneName
                else:
                    break
        self.initZoneInspector(newZoneName)
        self.zoneInspector[newZoneName] = self.zoneInspector[oldZoneName]
        del self.zoneInspector[oldZoneName]

    def addPlaylistToDatabase(self, playlistPath):
        """ Add a playlist to the database. """
        playlistName = getPlaylistNameFromPath(playlistPath)
        self.playlists.append((playlistName, playlistPath))

    def removePlaylistFromDatabase(self, playlistRow):
        """ Remove a playlist from the database.

        Subsequently, remove it from every zone in the database.
        """
        playlistName = self.playlists[playlistRow][0]
        del self.playlists[playlistRow]
        for zone in self.zones:
            zoneName = zone[0]
            while True:
                zoneInspectorRow = self.getRowOfItemInColumnOfModel(
                                   playlistName, 0, self.zoneInspector[zoneName])
                if zoneInspectorRow is not None:
                    del self.zoneInspector[zoneName][zoneInspectorRow]
                else:
                    break

    def addZoneToSchedule(self, dayIndex, zoneName, zoneStartTime='00:00'):
        """ Add zoneName to the day that corresponds to dayIndex in Flow Schedule. """
        self.schedule[dayIndex].append((zoneStartTime, zoneName))

    def removeZoneFromSchedule(self, dayIndex, scheduleRow):
        """ Remove a zone from the day that corresponds to dayIndex in Flow Schedule. """
        del self.schedule[dayIndex][scheduleRow]

    def addPlaylistToZone(self, zoneName, playlist):
        """ Add playlist to zoneName. """
        self.zoneInspector[zoneName].append((
            playlist.name, playlist.type, playlist.shuffle, playlist.schedIntervalMins,
            playlist.numSchedItems, playlist.fadeInSecs, playlist.fadeOutSecs,
            playlist.minLevel, playlist.maxLevel))

    def removePlaylistFromZone(self, zoneName, zoneInspectorRow):
        """ Remove the playlist located in zoneInspectorRow from zoneName. """
        del self.zoneInspector[zoneName][zoneInspectorRow]

    def zoneExistsInDatabase(self, zoneName):
        """ Return true if zoneName exists in database. """
        return self.itemExistsInColumnOfModel(zoneName, 0, self.zones)

    def playlistExistsInDatabase(self, playlistName):
        """ Return true if playlistName exists in database. """
        return self.itemExistsInColumnOfModel(playlistName, 0, self.playlists)

    def zoneHasMainPlaylist(self, zoneName):
        """ Return true if zoneName has a Main playlist. """
        return self.itemExistsInColumnOfModel('Main', 1, self.zoneInspector[zoneName])

    def getZoneRow(self, zoneName):
        """ Return the zoneName's row in Zones. """
        return self.getRowOfItemInColumnOfModel(zoneName, 0, self.zones)

    def getPlaylistRow(self, playlistName):
        """ Return the playlistName's row in Playlists. """
        return self.getRowOfItemInColumnOfModel(playlistName, 0, self.playlists)

    def getMainPlaylistRow(self, zoneName):
        """ Return the Main playlist's row of zoneName in zoneInspector. """
        return self.getRowOfItemInColumnOfModel('Main', 1, self.zoneInspector[zoneName])

    def getFallbackPlaylistRow(self, zoneName):
        """ Return the Fallback playlist's row of zoneName in zoneInspector. """
        return self.getRowOfItemInColumnOfModel('Fallback', 1,
                                                self.zoneInspector[zoneName])

    def attemptToAddDefaultPlaylistsToZone(self, zoneName):
        """ Add default playlists to zoneName, if they exist in database. """
        if self.playlistExistsInDatabase('fallback'):
            playlist = Playlist('fallback', 'Fallback', True, '', '', '2', '2', '0', '1')
            self.addPlaylistToZone(zoneName, playlist)
        if self.playlistExistsInDatabase('Spots'):
            playlist = Playlist('Spots', 'Intermediate', True, '70', '1', '', '', '', '')
            self.addPlaylistToZone(zoneName, playlist)
        if self.playlistExistsInDatabase('Jingles'):
            playlist = Playlist('Jingles', 'Intermediate', True,
                                '40', '1', '', '', '', '')
            self.addPlaylistToZone(zoneName, playlist)


    # Private methods

    def itemExistsInColumnOfModel(self, item, column, model):
        """ If item exists in model's column, return true. """
        return any((row[column] == item for row in model))

    def getRowOfItemInColumnOfModel(self, item, column, model):
        """ If item exists in model's column, return its row. """
        for i in range(len(model)):
            treeiter = model.get_iter(TreePath(i))
            if model[treeiter][column] == item:
                return treeiter
        return None

    def initZoneInspector(self, zoneName):
        """ Initialize zoneName's inspector. """
        self.zoneInspector[zoneName] = ListStore(str, str, bool, str, str,
                                                 str, str, str, str)
        self.zoneInspector[zoneName].set_sort_column_id(1, SortType.DESCENDING)
