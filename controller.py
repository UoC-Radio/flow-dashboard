"""
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
from gi.repository.Gtk import Application, Builder, Entry, MessageType, ResponseType,\
                              EntryCompletion
from gi.repository.Gio import SimpleAction
from gi.repository.GLib import idle_add
from lxml import etree as ET
from xml.dom.minidom import parseString
from urllib.request import urlopen
from threading import Thread
from time import sleep

from helpers import Playlist, getPlaylistNameFromPath, MENU, XSD_SCHEMA_URL,\
                    XSD_SCHEMA_FALLBACK, WEEK, APP_TITLE, getHoursModel
from view import View
from model import Model


class Controller(Application):
    """ Coordinates communication between the Model and the View.

    The whole point of MVC is to seperate the data (Model) from the GUI (View),
    to make the design modular.

    Thanks to GTK+, the view is automatically updated
    whenever the model changes.
    """

    def __init__(self):
        super().__init__()

    def do_startup(self):
        """ Perform startup operations.

        Called once, on application startup.
        """
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
        # multiple models or views cannot exist.
        self.view = View(application=self, title=APP_TITLE)
        self.model = Model()

        # Pass view all the callbacks, to assign each one to the appropriate GUI object.
        self.view.setCallbacks(self.Callbacks(self.model, self.view, self.XML(
                                              self.model, self.view)))

        # Initialize the GUI
        self.view.initGUI()

        # Connect each view component with its corresponding model.
        # This is clearly a controller's responsibility.
        self.view.zones.set_model(self.model.zones)
        self.view.playlists.set_model(self.model.playlists)
        for dayIndex in range(7):
            self.view.schedule[dayIndex].set_model(self.model.schedule[dayIndex])

        # Set app title and logo in gnome's top bar
        self.view.set_wmclass('Flow Dashboard', 'Flow Dashboard')
        self.view.set_icon_from_file('gallery/logo.png')

        # Make the GUI visible
        self.view.show_all()

        # Zone Inspector is set initially invisible, until a zone is selected
        self.view.zoneInspector.hide()

    def do_activate(self):
        """ Perform activation operations.

        Called every time the user tries to start the app
        (even when it is already started).
        """
        # Give app the keyboard focus
        self.view.present()

    def on_quit(self, action, param):
        """ Perform cleanup operations.

        Called once, on application exit.
        """
        self.quit()


    class Callbacks:
        """ Handle user interaction with the GUI.

        Contains all the callback functions.

        Each function is called when a specific action is performed by the user,
        to fulfill the request that corresponds to that action.
        """

        def __init__(self, model, view, xml):
            self.model = model
            self.view = view
            self.xml = xml
            self.progressBarWindow = None

        def onAddZoneButtonClicked(self, button):
            """
            1) Display a dialog where the user can input the new zone name.
            2) Handle user input.

            Trigger:
                User clicks the "+" button in Zones header bar.
            """
            entry = Entry()
            addZoneDialog = self.view.dialogs.AddZone(self.view, entry)
            while True:
                response = addZoneDialog.run()
                if response == ResponseType.OK:
                    # Get user input from the dialog
                    zoneName = entry.get_text()
                    if not self.model.zoneExistsInDatabase(zoneName):
                        # Ζone is absent from the database.
                        # Αdd it and try to load it with the default playlists.
                        self.model.addZoneToDatabase(zoneName)
                        self.model.attemptToAddDefaultPlaylistsToZone(zoneName)
                        break
                    else:
                        # Zone already exists in database.
                        # Notify the user and let him retry.
                        self.view.Dialogs.showMessagePopup(addZoneDialog,
                            MessageType.ERROR, 'Error', 'Zone already exists.')
                else:
                    break
            addZoneDialog.destroy()

        def onRemoveZoneButtonClicked(self, button):
            """ Remove selected zone.

            Trigger:
                User clicks the "-" button in Zones header bar.
            """
            # Remove the selected Zones row.
            # If no Zones row is selected, nothing happens.
            rowToRemove = self.view.zones.get_selection().get_selected()[1]
            if rowToRemove is not None:
                self.model.removeZoneFromDatabase(rowToRemove)

        def onAddPlaylistButtonClicked(self, button):
            """
            1) Display a file chooser dialog where the user can select playlist files.
            2) Handle user selection.

            Trigger:
                User clicks the "+" button in Playlists header bar.
            """
            addPlaylistDialog = self.view.dialogs.AddPlaylist(self.view)
            response = addPlaylistDialog.run()
            if response == ResponseType.OK:
                # Get playlist paths from the dialog.
                # User can select more than one playlist files.
                playlistPaths = addPlaylistDialog.get_filenames()
                # Add playlists to database if they are absent from it
                for playlistPath in playlistPaths:
                    playlistName = getPlaylistNameFromPath(playlistPath)
                    if not self.model.playlistExistsInDatabase(playlistName):
                        self.model.addPlaylistToDatabase(playlistPath)
            addPlaylistDialog.destroy()

        def onRemovePlaylistButtonClicked(self, button):
            """ Remove selected playlist.

            Trigger:
                User clicks the "-" button in Playlists header bar.
            """
            # Remove the selected Playlists row.
            # If no Playlists row is selected, nothing happens.
            rowToRemove = self.view.playlists.get_selection().get_selected()[1]
            if rowToRemove is not None:
                self.model.removePlaylistFromDatabase(rowToRemove)

        def onRemoveZoneFromScheduleButtonClicked(self, button):
            """ Remove selected occurrence of a zone in the Flow Schedule.

            Trigger:
                User clicks the "-" button in Flow Schedule header bar.
            """
            # Remove the selected Flow Schedule row.
            # If no Flow Schedule row is selected, nothing happens.
            selectedDayIndex = self.view.scheduleNotebook.get_current_page()
            rowToRemove = self.view.schedule[
                          selectedDayIndex].get_selection().get_selected()[1]
            if rowToRemove is not None:
                self.model.removeZoneFromSchedule(selectedDayIndex, rowToRemove)

        def onRemovePlaylistFromZoneButtonClicked(self, button):
            """ Remove selected playlist from selected zone.

            Trigger:
                User clicks the "-" button in Zone Inspector header bar.
            """
            # Remove the selected Zone Inspector row.
            # If no Zone Inspector row is selected, nothing happens.
            rowToRemove = self.view.zoneInspector.get_selection().get_selected()[1]
            if rowToRemove is not None:
                zoneName = self.model.zones[
                           self.view.zones.get_selection().get_selected()[1]
                           ][0]
                self.model.removePlaylistFromZone(zoneName, rowToRemove)

        def onScheduleRowEditingStarted(self, renderer, editable, path, column):
            """ Activate autocompletion in the Flow Schedule cell that is being edited.

            Trigger:
                User starts editing a Flow Schedule row.
            """
            completion = EntryCompletion.new()
            model = self.model.zones if column == 1 else getHoursModel()
            completion.set_model(model)
            completion.set_text_column(0)
            editable.set_completion(completion)

        def onScheduleRowEdited(self, renderer, path, newString, dayIndex, column):
            """ Handle user input and update the model.

            Trigger:
                User finishes editing a Flow Schedule row.
            """
            if column != 1:
                # Update the model accordingly.
                self.model.schedule[dayIndex][path][column] = newString
            elif not self.model.zoneExistsInDatabase(newString):
                # New zone does not exist in database. Notify the user.
                self.view.Dialogs.showMessagePopup(self.view, MessageType.ERROR, 'Error',
                                                   'Zone does not exist in database.')
            elif self.model.schedule[dayIndex][path][column] != newString:
                # User changes a zone's name in Flow Schedule.
                # Update the model accordingly.
                self.model.schedule[dayIndex][path][column] = newString

        def onZoneRowEdited(self, renderer, path, newString, column):
            """ Handle user input and update the model.

            Trigger:
                User finishes editing a Zones row.
            """
            if column != 0:
                # Update the model accordingly.
                self.model.zones[path][column] = newString
            elif not self.model.zoneExistsInDatabase(newString):
                # User changes a zone's name in Zones.
                oldZoneName = self.model.zones[path][column]
                self.model.editZoneNameInDatabase(oldZoneName, newString)
            elif self.model.zones[path][column] != newString:
                # New zone already exists in database. Notify the user.
                self.view.Dialogs.showMessagePopup(self.view, MessageType.ERROR, 'Error',
                                                   'Zone already exists.')

        def onZoneInspectorRowEditingStarted(self, renderer, editable, path, column):
            """ Activate autocompletion in the Zone Inspector cell that is being edited.

            Trigger:
                User starts editing a Zone Inspector row.
            """
            if column == 0:
                completion = EntryCompletion.new()
                completion.set_model(self.model.playlists)
                completion.set_text_column(0)
                editable.set_completion(completion)

        def onZoneInspectorRowEdited(self, renderer, path, newString, column):
            """ Handle user input and update the model.

            Trigger:
                User finishes editing a Zone Inspector row.
            """
            zoneSelected = self.model.zones[
                           self.view.zones.get_selection().get_selected()[1]
                           ][0]
            if column != 0:
                # Update the model accordingly.
                self.model.zoneInspector[zoneSelected][path][column] = newString
            elif not self.model.playlistExistsInDatabase(newString):
                # New playlist does not exist in database. Notify the user.
                self.view.Dialogs.showMessagePopup(self.view, MessageType.ERROR, 'Error',
                                                   'Playlist does not exist in database.')
            elif self.model.zoneInspector[zoneSelected][path][column] != newString:
                # User changes a playlist's name in Zone Inspector.
                # Update the model accordingly.
                self.model.zoneInspector[zoneSelected][path][column] = newString

        def onPlaylistTypeChanged(self, widget, path, newPlaylistType):
            """ Update the model.

            Trigger:
                User selects a playlist type.
            """
            # Get selected zone and update the model accordingly.
            zoneSelected = self.model.zones[
                           self.view.zones.get_selection().get_selected()[1]
                           ][0]
            self.model.zoneInspector[zoneSelected][path][1] = newPlaylistType

        def onShuffleToggled(self, renderer, path, column):
            """ Update the model.

            Trigger:
                User clicks the "Shuffle" checkbox.
            """
            # Get selected zone and update the model accordingly.
            zoneSelected = self.model.zones[
                           self.view.zones.get_selection().get_selected()[1]
                           ][0]
            self.model.zoneInspector[zoneSelected][path][column] = not\
            self.model.zoneInspector[zoneSelected][path][column]

        def onDragDataDraggedZone(self, zones, drag_context, data, info, time):
            """ Save dragged zone's name.

            Trigger:
                User begins dragging a Zone row.
            """
            # Write dragged zone's name in "data" buffer
            zoneDragged = self.model.zones[zones.get_selection().get_selected()[1]][0]
            data.set_text(zoneDragged, -1)

        def onDragDataDraggedPlaylist(self, playlists, drag_context, data, info, time):
            """ Save dragged playlist's name.

            Trigger:
                User begins dragging a Playlist row.
            """
            # Write dragged playlist's name in "data" buffer
            playlistDragged = self.model.playlists[
                              playlists.get_selection().get_selected()[1]
                              ][0]
            data.set_text(playlistDragged, -1)

        def onDragDataDroppedZone(self, schedule, drag_context, x, y, data, info, time):
            """ Retrieve dropped zone's name and update selected day.

            Trigger:
                User drops a Zone row in the Flow Schedule.
            """
            selectedDayIndex = self.view.scheduleNotebook.get_current_page()
            # Add dropped zone to selected Flow Schedule day, getting its name
            # from "data" buffer.
            self.model.addZoneToSchedule(selectedDayIndex, data.get_text())

        def onDragDataDroppedPlaylist(self, zoneInspector, drag_context, x, y,
                                      data, info, time):
            """ Retrieve dropped playlist's name and update selected zone.

            Trigger:
                User drops a Playlist row in the Zone Inspector.
            """
            selectedDayIndex = self.view.scheduleNotebook.get_current_page()
            zoneSelected = self.model.zones[
                           self.view.zones.get_selection().get_selected()[1]
                           ][0]
            # Add dropped playlist to selected zone as Main playlist,
            # getting its name from "data" buffer.
            # If the zone has already a Main playlist, add it as Intermediate.
            if not self.model.zoneHasMainPlaylist(zoneSelected):
                playlist = Playlist(data.get_data().decode('unicode-escape'),
                                    'Main', True, '', '', '1', '1', '0', '1')
            else:
                playlist = Playlist(data.get_data().decode('unicode-escape'),
                                    'Intermediate', True, '30', '1', '1', '1',
                                    '0', '1')
            self.model.addPlaylistToZone(zoneSelected, playlist)

        def onZoneRowSelected(self, selection):
            """ Update the GUI.

            Trigger:
                User selects a Zone row.
            """
            zoneRowSelected = selection.get_selected()[1]
            if zoneRowSelected is not None:
                # Make Zone Inspector display the contents of selected zone.
                # Do this by connecting Zone Inspector's view with selected
                # zone's model
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

        def onPlaylistRowSelected(self, selection):
            """ Update the GUI.

            Trigger:
                User selects a Playlist row.
            """
            playlistRowSelected = selection.get_selected()[1]
            if playlistRowSelected is not None:
                # Enable "-" button in Playlists header bar
                self.view.removePlaylistButton.set_sensitive(True)
            else:
                # Disable "-" button in Playlists header bar
                self.view.removePlaylistButton.set_sensitive(False)

        def onScheduleRowSelected(self, selection):
            """ Update the GUI.

            Trigger:
                User selects a Flow Schedule row.
            """
            scheduleRowSelected = selection.get_selected()[1]
            if scheduleRowSelected is not None:
                # Enable "-" button in Flow Schedule header bar
                self.view.removeZoneFromScheduleButton.set_sensitive(True)
            else:
                # Disable "-" button in Flow Schedule header bar
                self.view.removeZoneFromScheduleButton.set_sensitive(False)

        def onScheduleDaySelected(self, schedule, day, dayIndex):
            """ Update the GUI.

            Trigger:
                User selects a Flow Schedule day.
            """
            scheduleRowSelected = self.view.schedule[
                                  dayIndex].get_selection().get_selected()[1]
            if scheduleRowSelected is not None:
                # Enable "-" button in Flow Schedule header bar
                self.view.removeZoneFromScheduleButton.set_sensitive(True)
            else:
                # Disable "-" button in Flow Schedule header bar
                self.view.removeZoneFromScheduleButton.set_sensitive(False)

        def onZoneInspectorRowSelected(self, selection):
            """ Update the GUI.

            Trigger:
                User selects a Zone Inspector row.
            """
            zoneInspectorRowSelected = selection.get_selected()[1]
            if zoneInspectorRowSelected is not None:
                # Enable "-" button in Zone Inspector header bar
                self.view.removePlaylistFromZoneButton.set_sensitive(True)
            else:
                # Disable "-" button in Zone Inspector header bar
                self.view.removePlaylistFromZoneButton.set_sensitive(False)

        def onImportXMLMenuOptionSelected(self, action, value):
            """
            1) Display a file chooser dialog where the user can select an XML file.
            2) Initiate the import of the selected file.

            Trigger:
                User clicks the Import XML menu option.
            """
            # Create a dialog to let user select the xml file to import
            importXMLDialog = self.view.dialogs.ImportXML(self.view)
            # Show the dialog
            response = importXMLDialog.run()
            if response == ResponseType.OK:
                # User clicks the dialog's Import button
                # Get the file path of the XML file to be imported
                xmlPath = importXMLDialog.get_filename()
                # Create and show the progress bar
                self.progressBarWindow = self.view.Windows.ProgressBar(
                                         self.view, 'Import Progress')
                self.progressBarWindow.show_all()
                # Execute import in a seperate thread, to let the main thread
                # handle GUI activity
                Thread(target=self.xml.importXML, args=(xmlPath,
                       self.progressBarWindow.update,
                       self.progressBarWindow.destroy)).start()
            importXMLDialog.destroy()

        def onExportXMLMenuOptionSelected(self, action, value):
            """
            1) Display a file chooser dialog where the user can select a filename.
            2) Initiate the export of the GUI content as XML data to the selected file.

            Trigger:
                User clicks the Export XML menu option.
            """
            # Create a dialog to let user type the xml filename to export
            exportXMLDialog = self.view.dialogs.ExportXML(self.view)
             # Show the dialog
            response = exportXMLDialog.run()
            if response == ResponseType.OK:
                # User clicks the dialog's Export button
                # Get the file path of the XML file to be exported
                xmlPath = exportXMLDialog.get_filename()
                # Create and show the progress bar
                self.progressBarWindow = self.view.Windows.ProgressBar(
                                         self.view, 'Export Progress')
                self.progressBarWindow.show_all()
                # Execute export in a seperate thread, to let the main thread
                # handle GUI activity
                Thread(target=self.xml.exportXML, args=(xmlPath,
                       self.progressBarWindow.update,
                       self.progressBarWindow.destroy)).start()
            exportXMLDialog.destroy()


    class XML:
        """ Perform XML-related operations. """

        def __init__(self, model, view):
            self.model = model
            self.view = view
            self.xmlSchema = None

        def importXML(self, inputXmlPath, updateProgressBar, destroyProgressBar):
            """ Import the XML file selected by the user.

            Use idle_add to make non-blocking requests
            for GUI-related operations to the main thread.
            """
            # Parse input XML file
            parser = ET.XMLParser(remove_comments=True)
            with open(inputXmlPath) as inputXmlFile:
                try:
                    tree = ET.parse(inputXmlFile, parser)
                except Exception as e:
                    print('Failed to parse input XML.\n' + str(e))
                    idle_add(self.view.Dialogs.showMessagePopup, self.view,
                             MessageType.ERROR, 'Error',
                             'Failed to parse input XML.',
                             str(e), 'Import aborted.')
                    idle_add(destroyProgressBar)
                    return
            idle_add(updateProgressBar)
            sleep(0.1)

            # Download and parse XSD schema
            if self.xmlSchema is None:
                self.downloadAndParseXSDSchema()
            idle_add(updateProgressBar)
            sleep(0.1)

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
                idle_add(self.view.Dialogs.showMessagePopup, self.view,
                         MessageType.WARNING, 'Warning',
                         'Validation of input won\'t be performed.')
            idle_add(updateProgressBar)
            sleep(0.1)

            # Do import

            # Get a day of the week
            for dayIndex, day in enumerate(root.getchildren()):

                # Import its zones one by one
                for zone in day.getchildren():
                    self.importZone(zone, dayIndex)
                idle_add(updateProgressBar)
                sleep(0.1)

            # Add imported file's location to main window title
            self.view.set_title(inputXmlPath + ' \u2014 ' + APP_TITLE)
            idle_add(destroyProgressBar)

        def importZone(self, zoneElement, dayIndex):
            """
            1) Add zone to Flow Schedule.
            2) Add it to the Zones database.
            3) Import its playlists.
            """
            # Get the name and start time of a zone to add it to the Flow Schedule
            zoneName = zoneElement.get('Name')
            zoneStartTime = zoneElement.get('Start')[:-3]    # Use -3 to ignore seconds
            self.model.addZoneToSchedule(dayIndex, zoneName, zoneStartTime)

            # Do not parse this zone element if the zone is
            # already (parsed and) added to the database.
            # It is assumed that every occurrence of a zone in the Flow Schedule
            # is identical to all the other occurrences of the same zone.
            # Thus, it only has to be parsed once, the first time it is encountered.
            if not self.model.zoneExistsInDatabase(zoneName):

                # Get the zone's metadata and add it to the database
                zoneMaintainers = zoneDescription = zoneComments = ''
                maintainerElement = zoneElement.find('Maintainer')
                if maintainerElement is not None:
                        zoneMaintainers = maintainerElement.text
                descriptionElement = zoneElement.find('Description')
                if descriptionElement is not None:
                        zoneDescription = descriptionElement.text
                commentElement = zoneElement.find('Comment')
                if commentElement is not None:
                        zoneComments = commentElement.text
                self.model.addZoneToDatabase(zoneName, zoneMaintainers,
                                             zoneDescription, zoneComments)

                # Import its playlists one by one
                for zoneChild in zoneElement.getchildren():
                    if zoneChild.tag in ['Main', 'Intermediate', 'Fallback']:
                        self.importPlaylist(zoneName, zoneChild)

        def importPlaylist(self, zoneName, playlistElement):
            """
            1) Add playlist to zoneName's inspector.
            2) Add it to the Playlists database.
            """
            # Parse this playlist element.
            # Note that, unlike the zones, it has to be parsed every time it is
            # encountered because its configuration settings may differ
            # depending on the zone it appears in.
            playlist = Playlist()
            playlist.type = playlistElement.tag
            for playlistChild in playlistElement.getchildren():
                if playlistChild.tag == 'Path':
                    playlist.name = getPlaylistNameFromPath(playlistChild.text)

                    # In case it is the first time this playlist is encountered,
                    # add it to the database.
                    if not self.model.playlistExistsInDatabase(playlist.name):
                        self.model.addPlaylistToDatabase(playlistChild.text)

                if playlistChild.tag == 'Shuffle':
                    playlist.shuffle = (playlistChild.text == 'true')
                if playlistChild.tag == 'Fader':
                    for faderChild in playlistChild.getchildren():
                        if faderChild.tag == 'FadeInDurationSecs':
                            playlist.fadeInSecs = faderChild.text
                        if faderChild.tag == 'FadeOutDurationSecs':
                            playlist.fadeOutSecs = faderChild.text
                        if faderChild.tag == 'MinLevel':
                            playlist.minLevel = faderChild.text
                        if faderChild.tag == 'MaxLevel':
                            playlist.maxLevel = faderChild.text
                if playlistChild.tag == 'SchedIntervalMins':
                    playlist.schedIntervalMins = playlistChild.text
                if playlistChild.tag == 'NumSchedItems':
                    playlist.numSchedItems = playlistChild.text
            self.model.addPlaylistToZone(zoneName, playlist)

        def exportXML(self, outputXmlPath, updateProgressBar, destroyProgressBar):
            """ Export the GUI content to an XML file.

            Use idle_add to make non-blocking requests
            for GUI-related operations to the main thread.
            """
            # Create week element
            weekElement = ET.Element('WeekSchedule')

            # Add days to week
            for dayIndex, day in enumerate(WEEK):
                dayElement = ET.SubElement(weekElement, day[:3])

                # Add zones to day
                for scheduleRow in self.model.schedule[dayIndex]:
                    self.exportZone(scheduleRow, dayElement)
                idle_add(updateProgressBar)
                sleep(0.1)

            # Remove empty elements
            self.clearEmptyElements(weekElement)

            # Download and parse XSD schema
            if self.xmlSchema is None:
                self.downloadAndParseXSDSchema()
            idle_add(updateProgressBar)
            sleep(0.1)

            # Validate output XML data against schema
            if self.xmlSchema is not None:
                print('Validating output XML ...')
                failureMessage = 'Export aborted.'
                if not self.validateXML(weekElement, failureMessage):
                    idle_add(destroyProgressBar)
                    return
            else:
                print('Validation of output won\'t be performed.')
                idle_add(self.view.Dialogs.showMessagePopup, self.view,
                         MessageType.WARNING, 'Warning',
                         'Validation of output won\'t be performed.')
            idle_add(updateProgressBar)
            sleep(0.1)

            # Output XML data to file
            with open(outputXmlPath, 'w') as f:
                dom = parseString(ET.tostring(weekElement))
                f.write(dom.toprettyxml(indent='\t', encoding='UTF-8').decode())
                idle_add(self.view.Dialogs.showMessagePopup, self.view,
                         MessageType.INFO, 'Info', 'Export successful.')
            idle_add(updateProgressBar)
            sleep(0.1)
            idle_add(destroyProgressBar)

        def exportZone(self, scheduleRow, dayElement):
            """
            1) Add scheduleRow's zone with its metadata to dayElement
            2) Export its playlists
            """
            zoneStartTime = scheduleRow[0]
            zoneName = scheduleRow[1]
            zoneElement = ET.SubElement(dayElement, 'Zone')
            zoneElement.set('Name', zoneName)
            zoneElement.set('Start', zoneStartTime + ':00')
            zoneRow = self.model.getZoneRow(zoneName)
            ET.SubElement(zoneElement, 'Maintainer').text = self.model.zones[zoneRow][2]
            ET.SubElement(zoneElement, 'Description').text = self.model.zones[zoneRow][1]
            ET.SubElement(zoneElement, 'Comment').text = self.model.zones[zoneRow][3]

            # Add playlists to zone
            self.exportPlaylists(zoneName, zoneElement)

        def exportPlaylists(self, zoneName, zoneElement):
            """ Add zoneName's playlists to zoneElement """
            # Add Main
            mainPlaylistRow = self.model.getMainPlaylistRow(zoneName)
            if mainPlaylistRow is not None:
                playlistElement = ET.SubElement(zoneElement, 'Main')
                self.fillPlaylistElement(playlistElement, self.model.zoneInspector[
                                                           zoneName][mainPlaylistRow])

            # Add Fallback
            fallbackPlaylistRow = self.model.getFallbackPlaylistRow(zoneName)
            if fallbackPlaylistRow is not None:
                playlistElement = ET.SubElement(zoneElement, 'Fallback')
                self.fillPlaylistElement(playlistElement, self.model.zoneInspector[
                                                           zoneName][fallbackPlaylistRow])

            # Add Intermediates
            for zoneInspectorRow in self.model.zoneInspector[zoneName]:
                if zoneInspectorRow[1] == 'Intermediate':
                    intermediatePlaylistRow = zoneInspectorRow
                    playlistElement = ET.SubElement(zoneElement, 'Intermediate')
                    playlistElement.set('Name', intermediatePlaylistRow[0])
                    self.fillPlaylistElement(playlistElement, intermediatePlaylistRow)

        def downloadAndParseXSDSchema(self):
            """ Download XSD schema from the web and parse it.

            In case of download failure, use the hardcoded schema.
            In case of parse failure, notify the user.
            """
            try:
                xsdSchemaFile = urlopen(XSD_SCHEMA_URL, timeout=3)
            except Exception as e:
                print('Failed to download XSD schema.\n' + str(e))
                print('Using hardcoded XSD schema ...')
                try:
                    self.xmlSchema = ET.XMLSchema(ET.fromstring(
                                     XSD_SCHEMA_FALLBACK.encode('utf-8')))
                except Exception as e:
                    print('Failed to parse XSD schema.\n' + str(e))
                    idle_add(self.view.Dialogs.showMessagePopup, self.view,
                             MessageType.ERROR, 'Error',
                             'Failed to parse XSD schema.', str(e))
            else:
                print('Got XSD Schema from', XSD_SCHEMA_URL)
                try:
                    self.xmlSchema = ET.XMLSchema(ET.parse(xsdSchemaFile))
                except Exception as e:
                    print('Failed to parse XSD schema.\n' + str(e))
                    idle_add(self.view.Dialogs.showMessagePopup, self.view,
                             MessageType.ERROR, 'Error',
                             'Failed to parse XSD schema.', str(e))

        def validateXML(self, rootElement, failureMessage):
            """ Validate the contents of rootElement.

            In case of validation failure, notify the user with failureMessage.
            """
            try:
                self.xmlSchema.assertValid(rootElement)
            except Exception as e:
                print('Validation failed.\n' + str(e))
                idle_add(self.view.Dialogs.showMessagePopup, self.view,
                         MessageType.ERROR, 'Error',
                         'Validation failed.', str(e), failureMessage)
                return False
            else:
                print('Validation successful.')
            return True

        def fillPlaylistElement(self, playlistElement, zoneInspectorRow):
            """ Construct a playlist element from zoneInspectorRow contents. """
            playlistRow = self.model.getPlaylistRow(zoneInspectorRow[0])
            ET.SubElement(playlistElement, 'Path').text = self.model.playlists[
                                                             playlistRow][1]
            ET.SubElement(playlistElement, 'Shuffle').text =\
                'true' if zoneInspectorRow[2] else 'false'
            faderElement = ET.SubElement(playlistElement, 'Fader')
            ET.SubElement(faderElement, 'FadeInDurationSecs').text = zoneInspectorRow[5]
            ET.SubElement(faderElement, 'FadeOutDurationSecs').text = zoneInspectorRow[6]
            ET.SubElement(faderElement, 'MinLevel').text = zoneInspectorRow[7]
            ET.SubElement(faderElement, 'MaxLevel').text = zoneInspectorRow[8]
            ET.SubElement(playlistElement, 'SchedIntervalMins').text = zoneInspectorRow[3]
            ET.SubElement(playlistElement, 'NumSchedItems').text = zoneInspectorRow[4]

        def clearEmptyElements(self, root):
            """ Remove root's empty children. """
            context = ET.iterwalk(root)
            for _, elem in context:
                parent = elem.getparent()
                if parent is not None and self.isRecursivelyEmpty(elem):
                    parent.remove(elem)

        def isRecursivelyEmpty(self, e):
            """ Determine whether an element e is recursively empty. """
            if e.text is not None and e.text != '':
                return False
            return all((self.isRecursivelyEmpty(c) for c in e.iterchildren()))
