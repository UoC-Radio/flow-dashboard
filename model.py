"""
Flow Dashboard - A flow schedule and zone management app

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

"""
Holds the application's data, as well as operations on them.
The four different models correspond to the four main window parts:
The Flow Schedule, the Zones, the Zone Inspector, and the Playlists.
"""
class Model:

	"""
	Initializes the four models except from zoneInspector,
	as no zone exists on application startup.
	"""
	def __init__(self):
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


	## Public methods ##
	"""
	Adds a zone to database.
	Consequently, it initializes its inspector.
	"""
	def addZoneToDatabase(self, zoneName, zoneMaintainers='', zoneDescription='', zoneComments=''):
		self.zones.append((zoneName, zoneDescription, zoneMaintainers, zoneComments))
		self.initZoneInspector(zoneName)

	"""
	Removes a zone from the database.
	Consequently, it deletes every occurrence of it in the Flow Schedule and also deletes its inspector.
	"""
	def removeZoneFromDatabase(self, zoneRow):
		zoneName = self.zones[zoneRow][0]
		del self.zones[zoneRow]
		for dayIndex in range(7):
			while True:
				scheduleRow = self.getRowOfItemInColumnOfModel(zoneName, 1, self.schedule[dayIndex])
				if scheduleRow is not None:
					del self.schedule[dayIndex][scheduleRow]
				else:
					break
		self.zoneInspector[zoneName].clear()
		del self.zoneInspector[zoneName]

	"""
	Edits a zone's name in the database.
	Consequently, it renames all its instances in the Flow Schedule and its Zone Inspector.
	"""
	def editZoneNameInDatabase(self, oldZoneName, newZoneName):
		zoneRow = self.getZoneRow(oldZoneName)
		self.zones[zoneRow][0] = newZoneName
		for dayIndex in range(7):
			while True:
				scheduleRow = self.getRowOfItemInColumnOfModel(oldZoneName, 1, self.schedule[dayIndex])
				if scheduleRow is not None:
					self.schedule[dayIndex][scheduleRow][1] = newZoneName
				else:
					break
		self.initZoneInspector(newZoneName)
		self.zoneInspector[newZoneName] = self.zoneInspector[oldZoneName]
		del self.zoneInspector[oldZoneName]


	""" Adds a playlist to database. """
	def addPlaylistToDatabase(self, playlistPath):
		playlistName = getPlaylistNameFromPath(playlistPath)
		self.playlists.append((playlistName, playlistPath))

	"""
	Removes a playlist from the database.
	Consequently, it removes it from every zone in the database.
	"""
	def removePlaylistFromDatabase(self, playlistRow):
		playlistName = self.playlists[playlistRow][0]
		del self.playlists[playlistRow]
		for zone in self.zones:
			zoneName = zone[0]
			while True:
				zoneInspectorRow = self.getRowOfItemInColumnOfModel(playlistName, 0, self.zoneInspector[zoneName])
				if zoneInspectorRow is not None:
					del self.zoneInspector[zoneName][zoneInspectorRow]
				else:
					break

	""" Adds zoneName to the day that corresponds to dayIndex in the Flow Schedule. """
	def addZoneToSchedule(self, dayIndex, zoneName, zoneStartTime='00:00'):
		self.schedule[dayIndex].append((zoneStartTime, zoneName))

	""" Removes a zone from the day that corresponds to dayIndex in the Flow Schedule. """
	def removeZoneFromSchedule(self, dayIndex, scheduleRow):
		del self.schedule[dayIndex][scheduleRow]

	""" Adds playlist to zoneName. """
	def addPlaylistToZone(self, zoneName, playlist):
		self.zoneInspector[zoneName].append((playlist.name, playlist.type, playlist.shuffle, playlist.schedIntervalMins, playlist.numSchedItems, playlist.fadeInSecs, playlist.fadeOutSecs, playlist.minLevel, playlist.maxLevel))

	""" Removes playlist located in zoneInspectorRow from zoneName. """
	def removePlaylistFromZone(self, zoneName, zoneInspectorRow):
		del self.zoneInspector[zoneName][zoneInspectorRow]

	""" Returns true if zoneName exists in the database. """
	def zoneExistsInDatabase(self, zoneName):
		return self.itemExistsInColumnOfModel(zoneName, 0, self.zones)

	""" Returns true if playlistName exists in the database. """
	def playlistExistsInDatabase(self, playlistName):
		return self.itemExistsInColumnOfModel(playlistName, 0, self.playlists)

	""" Returns true if zoneName has a Main playlist. """
	def zoneHasMainPlaylist(self, zoneName):
		return self.itemExistsInColumnOfModel('Main', 1, self.zoneInspector[zoneName])

	""" Returns the zoneName's row in Zones. """
	def getZoneRow(self, zoneName):
		return self.getRowOfItemInColumnOfModel(zoneName, 0, self.zones)

	""" Returns the playlistName's row in Playlists. """
	def getPlaylistRow(self, playlistName):
		return self.getRowOfItemInColumnOfModel(playlistName, 0, self.playlists)

	""" Returns the Main playlist's row of zoneName in zoneInspector. """
	def getMainPlaylistRow(self, zoneName):
		return self.getRowOfItemInColumnOfModel('Main', 1, self.zoneInspector[zoneName])

	""" Returns the Fallback playlist's row of zoneName in zoneInspector. """
	def getFallbackPlaylistRow(self, zoneName):
		return self.getRowOfItemInColumnOfModel('Fallback', 1, self.zoneInspector[zoneName])

	""" Adds default playlists to zoneName, if they exist in the database. """
	def attemptToAddDefaultPlaylistsToZone(self, zoneName):
		if self.playlistExistsInDatabase('fallback'):
			playlist = Playlist('fallback', 'Fallback', True, '', '', '2', '2', '0', '1')
			self.addPlaylistToZone(zoneName, playlist)
		if self.playlistExistsInDatabase('Spots'):
			playlist = Playlist('Spots', 'Intermediate', True, '70', '1', '', '', '', '')
			self.addPlaylistToZone(zoneName, playlist)
		if self.playlistExistsInDatabase('Jingles'):
			playlist = Playlist('Jingles', 'Intermediate', True, '40', '1', '', '', '', '')
			self.addPlaylistToZone(zoneName, playlist)


	## Private methods ##

	""" Returns true if item exists in model's column. """
	def itemExistsInColumnOfModel(self, item, column, model):
		return any((row[column] == item for row in model))

	""" If item exists in model's column, returns its row. """
	def getRowOfItemInColumnOfModel(self, item, column, model):
		for i in range(len(model)):
			treeiter = model.get_iter(TreePath(i))
			if model[treeiter][column] == item:
				return treeiter
		return None

	""" Initializes zoneName's Zone Inspector. """
	def initZoneInspector(self, zoneName):
		self.zoneInspector[zoneName] = ListStore(str, str, bool, str, str, str, str, str, str)
		self.zoneInspector[zoneName].set_sort_column_id(1, SortType.DESCENDING)
