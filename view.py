"""
The View

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

from gi.repository import Gtk, Gdk
from gi.repository.Gio import SimpleAction
from gi.repository.Pango import WrapMode
from helpers import CSS, WEEK


class View(Gtk.ApplicationWindow):
    """ The application's GUI. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Run initially maximized
        self.maximize()

        # Load CSS
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), style_provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Create dialogs and windows objects for controller access
        self.dialogs = self.Dialogs()
        self.windows = self.Windows()

    def setCallbacks(self, callbacks):
        """ Save the callbacks from controller.

        GUI items can then be connected to them.
        """
        self.callbacks = callbacks

    def activateMenu(self):
        """ Connect main menu options to callbacks """
        action = SimpleAction.new('import_xml', None)
        action.connect('activate', self.callbacks.onImportXMLMenuOptionSelected)
        self.add_action(action)
        action = SimpleAction.new('export_xml', None)
        action.connect('activate', self.callbacks.onExportXMLMenuOptionSelected)
        self.add_action(action)

    def initGUI(self):
        """ Initialize GUI components. """
        self.activateMenu()

        # Create outer grid
        self.outerContainer = Gtk.Grid()
        self.add(self.outerContainer)

        # Initialize components that sit on top of the outer grid
        self.initSchedule()
        self.initZones()
        self.initZoneInspector()
        self.initPlaylists()

    def initSchedule(self):
        """ Initialize Flow Schedule. """
        # Weekly Schedule Box
        self.scheduleBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.outerContainer.attach(self.scheduleBox, left=0, top=0, width=4, height=6)

        # Weekly Schedule HeaderBar
        self.scheduleHeaderBar = Gtk.HeaderBar(title='Flow Schedule',
                                               subtitle='Zones that play on air')
        self.removeZoneFromScheduleButton = Gtk.Button.new_from_icon_name(
                                            'list-remove-symbolic',
                                            Gtk.IconSize(Gtk.IconSize.BUTTON))
        self.removeZoneFromScheduleButton.get_style_context().add_class('minus-button')
        self.removeZoneFromScheduleButton.set_tooltip_text('Remove zone from schedule')
        self.removeZoneFromScheduleButton.connect(
            'clicked', self.callbacks.onRemoveZoneFromScheduleButtonClicked)
        self.removeZoneFromScheduleButton.set_sensitive(False)
        self.scheduleHeaderBar.pack_end(self.removeZoneFromScheduleButton)
        self.scheduleBox.add(self.scheduleHeaderBar)

        # Weekly Schedule View
        self.scheduleNotebook = Gtk.Notebook(tab_pos=Gtk.PositionType.TOP)
        self.scheduleNotebook.connect('switch-page', self.callbacks.onScheduleDaySelected)
        self.schedule = {}
        for dayIndex in range(7):
            self.schedule[dayIndex] = Gtk.TreeView()
            self.schedule[dayIndex].enable_model_drag_dest(
                [Gtk.TargetEntry.new('UTF8_STRING', Gtk.TargetFlags.SAME_APP, 0)],
                Gdk.DragAction.COPY)
            self.schedule[dayIndex].connect('drag-data-received',
                                            self.callbacks.onDragDataDroppedZone)
            self.schedule[dayIndex].get_selection().connect(
                'changed', self.callbacks.onScheduleRowSelected)
            for i, columnTitle in enumerate(['Hour', 'Name']):
                renderer = Gtk.CellRendererText(editable=True)
                renderer.connect('edited',
                                 self.callbacks.onScheduleRowEdited, dayIndex, i)
                renderer.connect('editing-started',
                                 self.callbacks.onScheduleRowEditingStarted, i)
                column = Gtk.TreeViewColumn(columnTitle, renderer, text=i)
                column.set_sort_column_id(i)
                self.schedule[dayIndex].append_column(column)
            scrollview = Gtk.ScrolledWindow()
            scrollview.set_vexpand(True)
            scrollview.add(self.schedule[dayIndex])
            self.scheduleNotebook.append_page(scrollview, Gtk.Label(WEEK[dayIndex]))
        self.scheduleBox.add(self.scheduleNotebook)

    def initZones(self):
        """ Initialize Zones. """
        # Zone Box
        self.zoneBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.outerContainer.attach(self.zoneBox, 4, 0, 8, 6)

        # Zone HeaderBar
        self.zoneHeaderBar = Gtk.HeaderBar(title='Zones', subtitle='Their database')
        self.removeZoneButton = Gtk.Button. new_from_icon_name(
            'list-remove-symbolic', Gtk.IconSize(Gtk.IconSize.BUTTON))
        self.removeZoneButton.get_style_context().add_class('minus-button')
        self.removeZoneButton.set_tooltip_text('Remove zone from database')
        self.removeZoneButton.connect('clicked', self.callbacks.onRemoveZoneButtonClicked)
        self.removeZoneButton.set_sensitive(False)
        self.zoneHeaderBar.pack_end(self.removeZoneButton)
        button = Gtk.Button. new_from_icon_name('list-add-symbolic',
                                                Gtk.IconSize(Gtk.IconSize.BUTTON))
        button.get_style_context().add_class('plus-button')
        button.set_tooltip_text('Add zone to database')
        button.connect('clicked', self.callbacks.onAddZoneButtonClicked)
        self.zoneHeaderBar.pack_end(button)
        self.zoneBox.add(self.zoneHeaderBar)

        # Zone View
        self.zones = Gtk.TreeView()
        self.zones.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new('UTF8_STRING', Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.COPY)
        self.zones.connect('drag-data-get', self.callbacks.onDragDataDraggedZone)
        self.zones.get_selection().connect('changed', self.callbacks.onZoneRowSelected)
        columnTitle = 'Name'
        renderer = Gtk.CellRendererText(editable=True)
        renderer.connect('edited', self.callbacks.onZoneRowEdited, 0)
        column = Gtk.TreeViewColumn(columnTitle, renderer, text=0)
        column.set_sort_column_id(0)
        self.zones.append_column(column)
        for i, columnTitle in enumerate(['Description', 'Maintainers', 'Comments']):
            renderer = Gtk.CellRendererText(editable=True)
            renderer.connect('edited', self.callbacks.onZoneRowEdited, i+1)
            renderer.props.wrap_width = 600
            renderer.props.wrap_mode = WrapMode.WORD_CHAR
            column = Gtk.TreeViewColumn(columnTitle, renderer, text=i+1)
            column.set_sort_column_id(i+1)
            column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
            column.set_resizable(True)
            self.zones.append_column(column)
        scrollview = Gtk.ScrolledWindow()
        scrollview.set_vexpand(True)
        scrollview.add(self.zones)
        self.zoneBox.add(scrollview)

    def initZoneInspector(self):
        """ Initialize Zone Inspector. """
        # Zone Inspector Box
        self.zoneInspectorBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                        hexpand=True)
        self.outerContainer.attach(self.zoneInspectorBox, 4, 6, 8, 6)

        # Zone Inspector HeaderBar
        self.zoneInspectorHeaderBar = Gtk.HeaderBar(title='Zone Inspector',
                                                    subtitle="Contents of selected zone")
        self.removePlaylistFromZoneButton = Gtk.Button.new_from_icon_name(
            'list-remove-symbolic', Gtk.IconSize(Gtk.IconSize.BUTTON))
        self.removePlaylistFromZoneButton.get_style_context().add_class('minus-button')
        self.removePlaylistFromZoneButton.set_tooltip_text('Remove playlist from zone')
        self.removePlaylistFromZoneButton.connect(
            'clicked', self.callbacks.onRemovePlaylistFromZoneButtonClicked)
        self.removePlaylistFromZoneButton.set_sensitive(False)
        self.zoneInspectorHeaderBar.pack_end(self.removePlaylistFromZoneButton)
        self.zoneInspectorBox.add(self.zoneInspectorHeaderBar)

        # Zone Inspector View
        self.zoneInspector = Gtk.TreeView()
        self.zoneInspector.enable_model_drag_dest(
            [Gtk.TargetEntry.new('text/plain', Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.COPY)
        self.zoneInspector.connect('drag-data-received',
                                   self.callbacks.onDragDataDroppedPlaylist)
        self.zoneInspector.get_selection().connect(
            'changed', self.callbacks.onZoneInspectorRowSelected)
        columnTitle = 'Name'
        renderer = Gtk.CellRendererText(editable=True)
        renderer.connect('edited', self.callbacks.onZoneInspectorRowEdited, 0)
        renderer.connect('editing-started',
                         self.callbacks.onZoneInspectorRowEditingStarted, 0)
        column = Gtk.TreeViewColumn(columnTitle, renderer, text=0)
        column.set_sort_column_id(0)
        self.zoneInspector.append_column(column)
        columnTitle = 'Type'
        renderer = Gtk.CellRendererCombo()
        renderer.set_property('editable', True)
        playlistTypes = Gtk.ListStore(str)
        playlistTypes.append(['Main'])
        playlistTypes.append(['Intermediate'])
        playlistTypes.append(['Fallback'])
        renderer.set_property('model', playlistTypes)
        renderer.set_property('text-column', 0)
        renderer.set_property('has-entry', False)
        renderer.connect('edited', self.callbacks.onPlaylistTypeChanged)
        column = Gtk.TreeViewColumn(columnTitle, renderer, text=1)
        column.set_sort_column_id(1)
        self.zoneInspector.append_column(column)
        columnTitle = 'Shuffle'
        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self.callbacks.onShuffleToggled, 2)
        column = Gtk.TreeViewColumn(columnTitle, renderer, active=2)
        column.set_sort_column_id(2)
        self.zoneInspector.append_column(column)
        for i, columnTitle in enumerate([
            'SchedIntervalMins', 'NumSchedItems', 'FadeInSecs', 'FadeOutSecs', 'MinLevel',
            'MaxLevel']):
            renderer = Gtk.CellRendererText(editable=True)
            renderer.connect('edited', self.callbacks.onZoneInspectorRowEdited, i+3)
            column = Gtk.TreeViewColumn(columnTitle, renderer, text=i+3)
            column.set_sort_column_id(i+3)
            self.zoneInspector.append_column(column)
        scrollview = Gtk.ScrolledWindow()
        scrollview.set_vexpand(True)
        scrollview.add(self.zoneInspector)
        self.zoneInspectorBox.add(scrollview)

    def initPlaylists(self):
        """ Initialize Playlists. """
        # Playlist Box
        self.playlistBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.outerContainer.attach(self.playlistBox, 0, 6, 4, 6)

        # Playlist HeaderBar
        self.playlistHeaderBar = Gtk.HeaderBar(title='Playlists',
                                               subtitle='Their database')
        self.removePlaylistButton = Gtk.Button. new_from_icon_name(
            'list-remove-symbolic', Gtk.IconSize(Gtk.IconSize.BUTTON))
        self.removePlaylistButton.get_style_context().add_class('minus-button')
        self.removePlaylistButton.set_tooltip_text('Remove playlist from database')
        self.removePlaylistButton.connect('clicked',
                                          self.callbacks.onRemovePlaylistButtonClicked)
        self.removePlaylistButton.set_sensitive(False)
        self.playlistHeaderBar.pack_end(self.removePlaylistButton)
        button = Gtk.Button. new_from_icon_name('list-add-symbolic',
                                                Gtk.IconSize(Gtk.IconSize.BUTTON))
        button.get_style_context().add_class('plus-button')
        button.set_tooltip_text('Add playlist to database')
        button.connect('clicked', self.callbacks.onAddPlaylistButtonClicked)
        self.playlistHeaderBar.pack_end(button)
        self.playlistBox.add(self.playlistHeaderBar)

        # Playlist View
        self.playlists = Gtk.TreeView()
        self.playlists.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK,
            [Gtk.TargetEntry.new('text/plain', Gtk.TargetFlags.SAME_APP, 0)],
            Gdk.DragAction.COPY)
        self.playlists.connect('drag-data-get', self.callbacks.onDragDataDraggedPlaylist)
        self.playlists.get_selection().connect('changed',
                                               self.callbacks.onPlaylistRowSelected)
        for i, columnTitle in enumerate(['Name', 'Path']):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(columnTitle, renderer, text=i)
            column.set_sort_column_id(i)
            self.playlists.append_column(column)
        scrollview = Gtk.ScrolledWindow()
        scrollview.set_vexpand(True)
        scrollview.add(self.playlists)
        self.playlistBox.add(scrollview)


    class Dialogs:
        """ All the dialogs that might be displayed. """

        def showMessagePopup(parent, type, title, message, details='', consequence=''):
            errorMessagePopup = Gtk.MessageDialog(parent, 0, type,
                                                  Gtk.ButtonsType.OK, title)
            errorMessagePopup.format_secondary_text(message)
            messageArea = errorMessagePopup.get_message_area()
            if details != '':
                messageArea.add(Gtk.Label(details))
            if consequence != '':
                messageArea.add(Gtk.Label(consequence))
            messageArea.show_all()
            errorMessagePopup.run()
            errorMessagePopup.destroy()


        class AddZone(Gtk.Dialog):

            def __init__(self, parent, entry):
                Gtk.Dialog.__init__(self, title='Add zone',
                                    transient_for=parent, modal=True)
                self.set_default_size(150, 100)
                self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
                okButton = self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)
                okButton.set_can_default(True)
                okButton.grab_default()
                label = Gtk.Label('Enter zone\'s name:')
                entry.set_activates_default(True)
                box = self.get_content_area()
                box.add(label)
                box.add(entry)
                self.show_all()


        class AddPlaylist(Gtk.FileChooserDialog):

            def __init__(self, parent):
                Gtk.FileChooserDialog.__init__(self, title='Choose a playlist file',
                                               transient_for=parent, modal=True,
                                               select_multiple=True,
                                               action=Gtk.FileChooserAction.OPEN)
                plsFilter = Gtk.FileFilter()
                plsFilter.set_name('Playlist files')
                plsFilter.add_pattern('*.pls')
                plsFilter.add_pattern('*.m3u')
                self.add_filter(plsFilter)
                allFilter = Gtk.FileFilter()
                allFilter.set_name('All files')
                allFilter.add_pattern('*')
                self.add_filter(allFilter)
                self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
                self.add_button(Gtk.STOCK_OPEN, Gtk.ResponseType.OK)


        class ImportXML(Gtk.FileChooserDialog):

            def __init__(self, parent):
                Gtk.FileChooserDialog.__init__(self, title='Choose an XML file',
                                               transient_for=parent, modal=True,
                                               action=Gtk.FileChooserAction.OPEN)
                xmlFilter = Gtk.FileFilter()
                xmlFilter.set_name('XML files')
                xmlFilter.add_pattern('*.xml')
                self.add_filter(xmlFilter)
                allFilter = Gtk.FileFilter()
                allFilter.set_name('All files')
                allFilter.add_pattern('*')
                self.add_filter(allFilter)
                self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
                self.add_button('Import', Gtk.ResponseType.OK)


        class ExportXML(Gtk.FileChooserDialog):

            def __init__(self, parent):
                Gtk.FileChooserDialog.__init__(
                    self, title='Choose a file name for the new XML schedule',
                    transient_for=parent, modal=True, action=Gtk.FileChooserAction.SAVE)
                self.set_do_overwrite_confirmation(True)
                xmlFilter = Gtk.FileFilter()
                xmlFilter.set_name('XML files')
                xmlFilter.add_pattern('*.xml')
                self.add_filter(xmlFilter)
                allFilter = Gtk.FileFilter()
                allFilter.set_name('All files')
                allFilter.add_pattern('*')
                self.add_filter(allFilter)
                self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
                self.add_button('Export', Gtk.ResponseType.OK)


    class Windows:
        """ All the windows that might be displayed, apart from the main window. """

        class ProgressBar(Gtk.Window):

            def __init__(self, parent, title):
                Gtk.Window.__init__(self, title=title, transient_for=parent,
                                    modal=True, resizable=False,
                                    window_position=Gtk.WindowPosition.CENTER_ON_PARENT)
                self.set_border_width(10)
                self.set_default_size(300, 40)
                self.progressBar = Gtk.ProgressBar(show_text=True)
                self.add(self.progressBar)

            # Updates the progress bar value
            def update(self):
                newValue = self.progressBar.get_fraction() + 0.1
                self.progressBar.set_fraction(newValue)
