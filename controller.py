"""
Flow Dashboard - A flow schedule and zone management app

The Controller

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

import gi
gi.require_version('Gtk', '3.0')
from gi.repository.Gtk import Application, Builder, Entry, MessageType, ResponseType, EntryCompletion
from gi.repository.Gio import SimpleAction
from gi.repository.GLib import idle_add
from lxml import etree
from xml.dom import minidom
from urllib.request import urlopen
from threading import Thread
from time import sleep

from helpers import Playlist, getPlaylistNameFromPath, MENU, XSD_FALLBACK_SCHEMA, WEEK, APP_TITLE, getHoursModel
from view import View
from model import Model

"""
Coordinates the communication between the Model and the View.
The whole point of MVC is to seperate the data (Model) from the GUI (View), to make the design more modular.
Thanks to GTK+, the view gets automatically updated whenever the model changes.
"""
class Controller(Application):

	def __init__(self):
		super().__init__()

	""" Called once, on application startup. """
	def do_startup(self):
		Application.do_startup(self)

		# Connect the close button to a callback
		action = SimpleAction.new('quit', None)
		action.connect('activate', self.on_quit)
		self.add_action(action)

		# Install main menu
		builder = Builder()
		builder.add_from_string(MENU)
		self.set_app_menu(builder.get_object('app-menu'))

		# Get a (single) view and model.
		# Because this function is executed only once,
		# we cannot have multiple models or views.
		self.view = View(application=self, title=APP_TITLE)
		self.model = Model()

		# Pass view all the callbacks, to assign each one to the appropriate GUI object.
		self.view.setCallbacks(self.Callbacks(self.model, self.view, self.XML(self.model, self.view)))

		# Initialize GUI
		self.view.initGUI()

		# Connect each view component with its corresponding model.
		# This is clearly a controller's responsibility.
		self.view.zones.set_model(self.model.zones)
		self.view.playlists.set_model(self.model.playlists)
		for dayIndex in range(7):
			self.view.schedule[dayIndex].set_model(self.model.schedule[dayIndex])

		# Make the GUI visible.
		# Note that Zone Inspector is set initially invisible, until a zone is selected.
		self.view.set_wmclass("Flow Dashboard", "Flow Dashboard")
		self.view.set_icon_from_file("gallery/logo.png")
		self.view.show_all()
		self.view.zoneInspector.hide()

	""" Called every time the user tries to start the app (even when it is already started). """
	def do_activate(self):
		# Give app the keyboard focus
		self.view.present()

	""" Called once, on application end. """
	def on_quit(self, action, param):
		self.quit()


	"""
	Contains all the callbacks. They handle user interaction with the GUI.
	Each function is called when a specific action is performed by the user.
	"""
	class Callbacks:

		def __init__(self, model, view, xml):
			self.model = model
			self.view = view
			self.xml = xml
			self.progressBarWindow = None

		""" User clicks the "+" button in Zones header bar. """
		def onAddZoneButtonClicked(self, button):
			entry = Entry()
			addZoneDialog = self.view.dialogs.AddZone(self.view, entry)
			while True:
				response = addZoneDialog.run()
				if response == ResponseType.OK:
					zoneName = entry.get_text()     # Get user input from the dialog
					if not self.model.zoneExistsInDatabase(zoneName):
						# Ζone is absent from the database. Αdd it and try to load it with the default playlists.
						self.model.addZoneToDatabase(zoneName)
						self.model.attemptToAddDefaultPlaylistsToZone(zoneName)
						break
					else:
						# Zone already exists in database. Notify the user and let him retry.
						self.view.Dialogs.showMessagePopup(addZoneDialog, MessageType.ERROR, 'Error', 'Zone already exists.')
				else:
					break
			addZoneDialog.destroy()

		""" User clicks the "-" button in Zones header bar. """
		def onRemoveZoneButtonClicked(self, button):
			# Remove the selected Zones row. If no Zones row is selected, nothing happens.
			rowToRemove = self.view.zones.get_selection().get_selected()[1]
			if rowToRemove is not None:
				self.model.removeZoneFromDatabase(rowToRemove)

		""" User clicks the "+" button in Playlists header bar. """
		def onAddPlaylistButtonClicked(self, button):
			addPlaylistDialog = self.view.dialogs.AddPlaylist(self.view)
			response = addPlaylistDialog.run()
			if response == ResponseType.OK:
				# Get playlist paths from the dialog. User can select more than one playlist files.
				playlistPaths = addPlaylistDialog.get_filenames()
				# Add playlists to database if they are absent from it
				for playlistPath in playlistPaths:
					playlistName = getPlaylistNameFromPath(playlistPath)
					if not self.model.playlistExistsInDatabase(playlistName):
						self.model.addPlaylistToDatabase(playlistPath)
			addPlaylistDialog.destroy()

		""" User clicks the "-" button in Playlists header bar. """
		def onRemovePlaylistButtonClicked(self, button):
			# Remove the selected Playlists row. If no Playlists row is selected, nothing happens.
			rowToRemove = self.view.playlists.get_selection().get_selected()[1]
			if rowToRemove is not None:
				self.model.removePlaylistFromDatabase(rowToRemove)

		""" User clicks the "-" button in Flow Schedule header bar. """
		def onRemoveZoneFromScheduleButtonClicked(self, button):
			# Remove the selected Flow Schedule row. If no Flow Schedule row is selected, nothing happens.
			selectedDayIndex = self.view.scheduleNotebook.get_current_page()
			rowToRemove = self.view.schedule[selectedDayIndex].get_selection().get_selected()[1]
			if rowToRemove is not None:
				self.model.removeZoneFromSchedule(selectedDayIndex, rowToRemove)

		""" User clicks the "-" button in Zone Inspector header bar. """
		def onRemovePlaylistFromZoneButtonClicked(self, button):
			# Remove the selected Zone Inspector row. If no Zone Inspector row is selected, nothing happens.
			rowToRemove = self.view.zoneInspector.get_selection().get_selected()[1]
			if rowToRemove is not None:
				zoneName = self.model.zones[self.view.zones.get_selection().get_selected()[1]][0]
				self.model.removePlaylistFromZone(zoneName, rowToRemove)

		""" User starts editing a Flow Schedule row. """
		def onScheduleRowEditingStarted(self, renderer, editable, path, column):
			completion = EntryCompletion.new()
			completion.set_model(self.model.zones if column == 1 else getHoursModel())
			completion.set_text_column(0)
			editable.set_completion(completion)

		""" User edits a Flow Schedule row. """
		def onScheduleRowEdited(self, renderer, path, newString, dayIndex, column):
			if column != 1:
				# Update the model accordingly.
				self.model.schedule[dayIndex][path][column] = newString
			elif not self.model.zoneExistsInDatabase(newString):
				# New zone does not exist in database. Notify the user.
				self.view.Dialogs.showMessagePopup(self.view, MessageType.ERROR, 'Error', 'Zone does not exist in database.')
			elif self.model.schedule[dayIndex][path][column] != newString:
				# User changes a zone's name in Flow Schedule.
				self.model.schedule[dayIndex][path][column] = newString

		""" User edits a Zones row. """
		def onZoneRowEdited(self, renderer, path, newString, column):
			if column != 0:
				# Update the model accordingly.
				self.model.zones[path][column] = newString
			elif not self.model.zoneExistsInDatabase(newString):
				# User changes a zone's name in Zones.
				oldZoneName = self.model.zones[path][column]
				self.model.editZoneNameInDatabase(oldZoneName, newString)
			elif self.model.zones[path][column] != newString:
				# New zone already exists in database. Notify the user.
				self.view.Dialogs.showMessagePopup(self.view, MessageType.ERROR, 'Error', 'Zone already exists.')

		""" User edits a Zone Inspector row. """
		def onZoneInspectorRowEdited(self, renderer, path, newString, column):
			zoneSelected = self.model.zones[self.view.zones.get_selection().get_selected()[1]][0]
			if column != 0:
				# Update the model accordingly.
				self.model.zoneInspector[zoneSelected][path][column] = newString
			elif not self.model.playlistExistsInDatabase(newString):
				# New playlist does not exist in database. Notify the user.
				self.view.Dialogs.showMessagePopup(self.view, MessageType.ERROR, 'Error', 'Playlist does not exist in database.')
			elif self.model.zoneInspector[zoneSelected][path][column] != newString:
				# User changes a playlist's name in Zone Inspector.
				self.model.zoneInspector[zoneSelected][path][column] = newString

		""" User changes the playlist type in a Zone Inspector row. """
		def onPlaylistTypeChanged(self, widget, path, newPlaylistType):
			# Get selected zone and update the model accordingly.
			zoneSelected = self.model.zones[self.view.zones.get_selection().get_selected()[1]][0]
			self.model.zoneInspector[zoneSelected][path][1] = newPlaylistType

		""" User clicks the "Shuffle" checkbox in a Zone Inspector row. """
		def onShuffleToggled(self, renderer, path, column):
			# Get selected zone and update the model accordingly.
			zoneSelected = self.model.zones[self.view.zones.get_selection().get_selected()[1]][0]
			self.model.zoneInspector[zoneSelected][path][column] = not self.model.zoneInspector[zoneSelected][path][column]

		""" User grabs a Zone row. """
		def onDragDataGrabbedZone(self, zones, drag_context, data, info, time):
			# Write grabbed zone's name in "data" buffer
			zoneGrabbed = self.model.zones[zones.get_selection().get_selected()[1]][0]
			data.set_text(zoneGrabbed, -1)

		""" User grabs a Playlist row. """
		def onDragDataGrabbedPlaylist(self, playlists, drag_context, data, info, time):
			# Write grabbed playlist's name in "data" buffer
			playlistGrabbed = self.model.playlists[playlists.get_selection().get_selected()[1]][0]
			data.set_text(playlistGrabbed, -1)

		""" User drops a row in the Flow Schedule. """
		def onDragDataReceivedZone(self, schedule, drag_context, x, y, data, info, time):
			selectedDayIndex = self.view.scheduleNotebook.get_current_page()
			# Add dropped zone to selected Flow Schedule day, getting its name from "data" buffer.
			self.model.addZoneToSchedule(selectedDayIndex, data.get_text())

		""" User drops a row in the Zone Inspector. """
		def onDragDataReceivedPlaylist(self, zoneInspector, drag_context, x, y, data, info, time):
			selectedDayIndex = self.view.scheduleNotebook.get_current_page()
			zoneSelected = self.model.zones[self.view.zones.get_selection().get_selected()[1]][0]
			# Add dropped playlist to selected zone as Main playlist, getting its name from "data" buffer.
			# If the zone has already a Main playlist, add it as Intermediate.
			if not self.model.zoneHasMainPlaylist(zoneSelected):
				playlist = Playlist(data.get_data().decode('unicode-escape'), 'Main', True, '', '', '1', '1', '0', '1')
			else:
				playlist = Playlist(data.get_data().decode('unicode-escape'), 'Intermediate', True, '30', '1', '1', '1', '0', '1')
			self.model.addPlaylistToZone(zoneSelected, playlist)

		""" User selects a Zone row. """
		def onZoneRowSelected(self, selection):
			# Make Zone Inspector display the contents of the currently selected zone,
			# or nothing if no zone is selected
			zoneRowSelected = selection.get_selected()[1]
			if zoneRowSelected is not None:
				# This is achieved by connecting zoneInspector view with the model of the currently selected zone
				zoneSelected = self.model.zones[zoneRowSelected][0]
				self.view.zoneInspector.set_model(self.model.zoneInspector[zoneSelected])
				# Show Zone Inspector
				if not self.view.zoneInspector.get_visible():
					self.view.zoneInspector.show()
				# Enable "-" button in Zones header bar
				self.view.removeZoneButton.set_sensitive(True)
			else:
				# No zone is selected
				# Hide Zone Inspector
				self.view.zoneInspector.hide()
				# Disable "-" button in Zones header bar
				self.view.removeZoneButton.set_sensitive(False)

		""" User selects a Playlist row. """
		def onPlaylistRowSelected(self, selection):
			playlistRowSelected = selection.get_selected()[1]
			if playlistRowSelected is not None:
				# Enable "-" button in Playlists header bar
				self.view.removePlaylistButton.set_sensitive(True)
			else:
				# Disable "-" button in Playlists header bar
				self.view.removePlaylistButton.set_sensitive(False)

		""" User selects a Flow Schedule row. """
		def onScheduleRowSelected(self, selection):
			scheduleRowSelected = selection.get_selected()[1]
			if scheduleRowSelected is not None:
				# Enable "-" button in Flow Schedule header bar
				self.view.removeZoneFromScheduleButton.set_sensitive(True)
			else:
				# Disable "-" button in Flow Schedule header bar
				self.view.removeZoneFromScheduleButton.set_sensitive(False)

		""" User selects a Flow Schedule day. """
		def onScheduleDaySelected(self, schedule, day, dayIndex):
			scheduleRowSelected = self.view.schedule[dayIndex].get_selection().get_selected()[1]
			if scheduleRowSelected is not None:
				# Enable "-" button in Flow Schedule header bar
				self.view.removeZoneFromScheduleButton.set_sensitive(True)
			else:
				# Disable "-" button in Flow Schedule header bar
				self.view.removeZoneFromScheduleButton.set_sensitive(False)

		""" User selects a Zone Inspector row. """
		def onZoneInspectorRowSelected(self, selection):
			zoneInspectorRowSelected = selection.get_selected()[1]
			if zoneInspectorRowSelected is not None:
				# Enable "-" button in Zone Inspector header bar
				self.view.removePlaylistFromZoneButton.set_sensitive(True)
			else:
				# Disable "-" button in Zone Inspector header bar
				self.view.removePlaylistFromZoneButton.set_sensitive(False)

		""" User clicks the Import XML menu option. """
		def onImportXMLMenuOptionSelected(self, action, value):
			importXMLDialog = self.view.dialogs.ImportXML(self.view)    # Create a dialog to let user select the xml file to import
			response = importXMLDialog.run()                            # Show the dialog
			if response == ResponseType.OK:                             # User clicks the dialog's Import button
				xmlPath = importXMLDialog.get_filename()                # Get the file path of the XML file to be imported
				self.progressBarWindow = self.view.Windows.ProgressBar(self.view, 'Import Progress')
				self.progressBarWindow.show_all()
				# Execute import in a seperate thread, to let the main thread handle GUI activity
				Thread(target=self.xml.importXML, args=(xmlPath, self.progressBarWindow.update, self.progressBarWindow.destroy)).start()
			importXMLDialog.destroy()

		""" User clicks the Export XML menu option. """
		def onExportXMLMenuOptionSelected(self, action, value):
			exportXMLDialog = self.view.dialogs.ExportXML(self.view)    # Create a dialog to let user type the xml filename to export
			response = exportXMLDialog.run()                            # Show the dialog
			if response == ResponseType.OK:                             # User clicks the dialog's Export button
				xmlPath = exportXMLDialog.get_filename()                # Get the file path of the XML file to be exported
				self.progressBarWindow = self.view.Windows.ProgressBar(self.view, 'Export Progress')
				self.progressBarWindow.show_all()
				# Execute export in a seperate thread, to let the main thread handle GUI activity
				Thread(target=self.xml.exportXML, args=(xmlPath, self.progressBarWindow.update, self.progressBarWindow.destroy)).start()
			exportXMLDialog.destroy()

	""" Contains XML-related operations. """
	class XML:

		def __init__(self, model, view):
			self.model = model
			self.view = view
			self.xmlSchema = None

		"""
		Imports the XML file selected by the user.
		idle_add is used to make (non-blocking) requests for GUI-related operations to the main thread.
		"""
		def importXML(self, inputXmlPath, updateProgressBar, destroyProgressBar):
			# Parse input XML file
			parser = etree.XMLParser(remove_comments=True)
			with open(inputXmlPath) as inputXmlFile:
				try:
					tree = etree.parse(inputXmlFile, parser)
				except Exception as e:
					print('Failed to parse input XML.\n' + str(e))
					idle_add(self.view.Dialogs.showMessagePopup, self.view, MessageType.ERROR, 'Error', 'Failed to parse input XML.', str(e), 'Import aborted.')
					idle_add(destroyProgressBar)
					return
			idle_add(updateProgressBar)

			# Download and parse XML schema
			if self.xmlSchema is None:
				self.downloadAndParseXMLSchema()
			idle_add(updateProgressBar)

			# Validate input XML file against schema
			root = tree.getroot()
			if self.xmlSchema is not None:
				print('Validating input XML ...')
				failureMessage = 'Import aborted.'
				if not self.validateXML(root, failureMessage):
					idle_add(destroyProgressBar)
					return
			else:
				print('Validation of input won\'t be performed.')
				idle_add(self.view.Dialogs.showMessagePopup, self.view, MessageType.WARNING, 'Warning', 'Validation of input won\'t be performed.')
			idle_add(updateProgressBar)

			# Do import
			week = root.getchildren()               # Get week element
			for dayIndex, day in enumerate(week):   # Get a day of the week
				idle_add(updateProgressBar)
				sleep(0.1)
				zones = day.getchildren()           # Get the zones of this day
				for zone in zones:
					# Only the name and the start time of a zone is needed to add it to the Flow Schedule.
					zoneName = zone.get('Name')
					zoneStartTime = zone.get('Start')[:-3]      # Use -3 to ignore seconds in the time format
					self.model.addZoneToSchedule(dayIndex, zoneName, zoneStartTime)
					# Do not parse the current zone if it is already (parsed and) added to database.
					# Here we assume that every occurrence of a zone in the Flow Schedule is identical
					# to all the other occurrences of the same zone. Thus, we only have to parse it once,
					# the first time we encounter it.
					if not self.model.zoneExistsInDatabase(zoneName):
						# Get the zone's metadata and add it to database
						zoneMaintainers = zoneDescription = zoneComments = ''
						if zone.find('Maintainer') is not None: zoneMaintainers = zone.find('Maintainer').text
						if zone.find('Description') is not None: zoneDescription = zone.find('Description').text
						if zone.find('Comment') is not None: zoneComments = zone.find('Comment').text
						self.model.addZoneToDatabase(zoneName, zoneMaintainers, zoneDescription, zoneComments)
						# Get the playlists of this zone
						for zoneChild in zone.getchildren():
							if zoneChild.tag == 'Main' or zoneChild.tag == 'Fallback' or zoneChild.tag == 'Intermediate':
								# Parse the current playlist.
								# Note that, unlike the zones, it has to be parsed every time it is encountered
								# because its configuration settings may differ depending on the zone it appears in.
								playlist = Playlist()
								playlist.type = zoneChild.tag
								for playlistChild in zoneChild.getchildren():
									if playlistChild.tag == 'Path':
										playlist.name = getPlaylistNameFromPath(playlistChild.text)
										if not self.model.playlistExistsInDatabase(playlist.name):
											self.model.addPlaylistToDatabase(playlistChild.text)
									if playlistChild.tag == 'Shuffle': playlist.shuffle = (playlistChild.text == 'true')
									if playlistChild.tag == 'Fader':
										for faderChild in playlistChild.getchildren():
											if faderChild.tag == 'FadeInDurationSecs': playlist.fadeInSecs = faderChild.text
											if faderChild.tag == 'FadeOutDurationSecs': playlist.fadeOutSecs = faderChild.text
											if faderChild.tag == 'MinLevel': playlist.minLevel = faderChild.text
											if faderChild.tag == 'MaxLevel': playlist.maxLevel = faderChild.text
									if playlistChild.tag == 'SchedIntervalMins': playlist.schedIntervalMins = playlistChild.text
									if playlistChild.tag == 'NumSchedItems': playlist.numSchedItems = playlistChild.text
								self.model.addPlaylistToZone(zoneName, playlist)
			self.view.set_title(inputXmlPath + ' \u2014 ' + APP_TITLE)
			idle_add(destroyProgressBar)

		"""
		Exports the GUI content to an XML file.
		idle_add is used to make (non-blocking) requests for GUI-related operations to the main thread.
		"""
		def exportXML(self, outputXmlPath, updateProgressBar, destroyProgressBar):
			# Create week element
			weekElement = etree.Element('WeekSchedule')

			# Add days to week
			for dayIndex, day in enumerate(WEEK):
				dayElement = etree.SubElement(weekElement, day[:3])

				# Add zones to day
				for scheduleRow in self.model.schedule[dayIndex]:
					zoneName = scheduleRow[1]
					zoneStartTime = scheduleRow[0]
					zoneElement = etree.SubElement(dayElement, 'Zone')
					zoneElement.set('Name', zoneName)
					zoneElement.set('Start', zoneStartTime + ':00')
					zoneRow = self.model.getZoneRow(zoneName)
					etree.SubElement(zoneElement, 'Maintainer').text = self.model.zones[zoneRow][2]
					etree.SubElement(zoneElement, 'Description').text = self.model.zones[zoneRow][1]
					etree.SubElement(zoneElement, 'Comment').text = self.model.zones[zoneRow][3]

					# Add playlists to zone
					# Add Main
					mainPlaylistRow = self.model.getMainPlaylistRow(zoneName)
					if mainPlaylistRow is not None:
						playlistElement = etree.SubElement(zoneElement, 'Main')
						self.fillPlaylistElement(playlistElement, self.model.zoneInspector[zoneName][mainPlaylistRow])

					# Add Fallback
					fallbackPlaylistRow = self.model.getFallbackPlaylistRow(zoneName)
					if fallbackPlaylistRow is not None:
						playlistElement = etree.SubElement(zoneElement, 'Fallback')
						self.fillPlaylistElement(playlistElement, self.model.zoneInspector[zoneName][fallbackPlaylistRow])

					# Add Intermediates
					for zoneInspectorRow in self.model.zoneInspector[zoneName]:
						if zoneInspectorRow[1] == 'Intermediate':
							intermediatePlaylistRow = zoneInspectorRow
							playlistElement = etree.SubElement(zoneElement, 'Intermediate')
							playlistElement.set('Name', intermediatePlaylistRow[0])
							self.fillPlaylistElement(playlistElement, intermediatePlaylistRow)

				idle_add(updateProgressBar)
				sleep(0.1)

			# Remove empty elements
			self.clearEmptyElements(weekElement)
			idle_add(updateProgressBar)

			# Download and parse XML schema
			if self.xmlSchema is None:
				self.downloadAndParseXMLSchema()
			idle_add(updateProgressBar)

			# Validate output XML data against schema
			if self.xmlSchema is not None:
				print('Validating output XML ...')
				failureMessage = 'Export aborted.'
				if not self.validateXML(weekElement, failureMessage):
					idle_add(destroyProgressBar)
					return
			else:
				print('Validation of output won\'t be performed.')
				idle_add(self.view.Dialogs.showMessagePopup, self.view, MessageType.WARNING, 'Warning', 'Validation of output won\'t be performed.')
			idle_add(updateProgressBar)

			# Output XML data to file
			with open(outputXmlPath, 'w') as f:
				dom = minidom.parseString(etree.tostring(weekElement))
				f.write(dom.toprettyxml(indent='\t', encoding='UTF-8').decode())
				idle_add(self.view.Dialogs.showMessagePopup, self.view, MessageType.INFO, 'Info', 'Export successful.')
			idle_add(updateProgressBar)
			sleep(0.1)
			idle_add(destroyProgressBar)

		"""
		Downloads the XML schema from the web and parses it.
		In case of download failure, it uses the hardcoded one.
		Notifies the user in case of parse failure.
		"""
		def downloadAndParseXMLSchema(self):
			xsdSchemaURL = 'https://raw.githubusercontent.com/UoC-Radio/audio-scheduler/master/config_schema.xsd'
			try:
				xsdSchemaFile = urlopen(xsdSchemaURL, timeout=3)
			except Exception as e:
				print('Failed to download XSD schema.\n' + str(e))
				print('Using hardcoded XSD schema ...')
				try:
					self.xmlSchema = etree.XMLSchema(etree.fromstring(XSD_FALLBACK_SCHEMA.encode('utf-8')))
				except Exception as e:
					print('Failed to parse XSD schema.\n' + str(e))
					idle_add(self.view.Dialogs.showMessagePopup, self.view, MessageType.ERROR, 'Error', 'Failed to parse XSD schema.', str(e))
			else:
				print('Got XSD Schema from', xsdSchemaURL)
				try:
					self.xmlSchema = etree.XMLSchema(etree.parse(xsdSchemaFile))
				except Exception as e:
					print('Failed to parse XSD schema.\n' + str(e))
					idle_add(self.view.Dialogs.showMessagePopup, self.view, MessageType.ERROR, 'Error', 'Failed to parse XSD schema.', str(e))

		"""
		Validates the contents of rootElement.
		Notifies the user in case of validation failure,
		providing some insight into why the validation failed.
		"""
		def validateXML(self, rootElement, failureMessage):
			try:
				self.xmlSchema.assertValid(rootElement)
			except Exception as e:
				print('Validation failed.\n' + str(e))
				idle_add(self.view.Dialogs.showMessagePopup, self.view, MessageType.ERROR, 'Error', 'Validation failed.', str(e), failureMessage)
				return False
			else:
				print('Validation successful.')
			return True

		""" Fills the playlistElement with the zoneInspectorRow contents. """
		def fillPlaylistElement(self, playlistElement, zoneInspectorRow):
			playlistRow = self.model.getPlaylistRow(zoneInspectorRow[0])
			etree.SubElement(playlistElement, 'Path').text = self.model.playlists[playlistRow][1]
			etree.SubElement(playlistElement, 'Shuffle').text = 'true' if zoneInspectorRow[2] else 'false'
			faderElement = etree.SubElement(playlistElement, 'Fader')
			etree.SubElement(faderElement, 'FadeInDurationSecs').text = zoneInspectorRow[5]
			etree.SubElement(faderElement, 'FadeOutDurationSecs').text = zoneInspectorRow[6]
			etree.SubElement(faderElement, 'MinLevel').text = zoneInspectorRow[7]
			etree.SubElement(faderElement, 'MaxLevel').text = zoneInspectorRow[8]
			etree.SubElement(playlistElement, 'SchedIntervalMins').text = zoneInspectorRow[3]
			etree.SubElement(playlistElement, 'NumSchedItems').text = zoneInspectorRow[4]

		""" Deletes root's (recursively) empty children. """
		def clearEmptyElements(self, root):
			context = etree.iterwalk(root)
			for _, elem in context:
				parent = elem.getparent()
				if parent is not None and self.isRecursivelyEmpty(elem):
					parent.remove(elem)

		""" Determines if an element e is recursively empty. """
		def isRecursivelyEmpty(self, e):
			if e.text is not None and e.text != '':
			   return False
			return all((self.isRecursivelyEmpty(c) for c in e.iterchildren()))
