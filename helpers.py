"""
Helpers

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

from os.path import basename
from gi.repository.Gtk import ListStore, SortType


""" Constants, functions, classes and embedded files that are used throughout the application. """

# Constants

APP_TITLE = 'Autopilot Schedule'

WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

XSD_SCHEMA_URL =\
'https://raw.githubusercontent.com/UoC-Radio/audio-scheduler/master/config_schema.xsd'


# Functions

HOURS = None

def getHoursModel():
    global HOURS
    if HOURS is None:
        HOURS = ListStore(str)
        HOURS.set_sort_column_id(0, SortType.ASCENDING)
        for i in range(24):
            HOURS.append((str(i).zfill(2) + ':00',))
    return HOURS

def getPlaylistNameFromPath(playlistPath):
    return basename(playlistPath).split('.')[0]


# Classes

class Playlist:

    def __init__(self, name='', type='', shuffle='', schedIntervalMins='', numSchedItems='',
                 fadeInSecs='', fadeOutSecs='', minLevel='', maxLevel=''):
        self.name = name
        self.type = type
        self.shuffle = shuffle
        self.schedIntervalMins = schedIntervalMins
        self.numSchedItems = numSchedItems
        self.fadeInSecs = fadeInSecs
        self.fadeOutSecs = fadeOutSecs
        self.minLevel = minLevel
        self.maxLevel = maxLevel


# Embedded files

CSS = """
.minus-button {
    background-color: darkred;
    background-blend-mode: luminosity;
}

.plus-button {
    background-color: darkgreen;
    background-blend-mode: luminosity;
}

progress, trough {
  min-height: 30px;
}
"""

MENU = """<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="app-menu">
      <section>
        <item>
          <attribute name="action">win.import_xml</attribute>
          <attribute name="label" translatable="yes">Import XML ...</attribute>
        </item>
        <item>
          <attribute name="action">win.export_xml</attribute>
          <attribute name="label" translatable="yes">Export XML ...</attribute>
        </item>
      </section>
  </menu>
</interface>
"""

XSD_SCHEMA_FALLBACK = """<?xml version="1.0" encoding="UTF-8" ?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">

<xs:simpleType name="FadeDurationSecs">
    <xs:restriction base="xs:integer">
        <xs:minInclusive value="0"/>
        <xs:maxInclusive value="10"/>
    </xs:restriction>
</xs:simpleType>

<xs:simpleType name="VolumeLevel">
    <xs:restriction base="xs:float">
        <xs:minInclusive value="0.0"/>
        <xs:maxInclusive value="1.0"/>
    </xs:restriction>
</xs:simpleType>

<xs:complexType name="Fader">
    <xs:sequence>
        <xs:element name="FadeInDurationSecs" type="FadeDurationSecs" minOccurs="0"/>
        <xs:element name="FadeOutDurationSecs" type="FadeDurationSecs" minOccurs="0"/>
        <xs:element name="MinLevel" type="VolumeLevel" minOccurs="0"/>
        <xs:element name="MaxLevel" type="VolumeLevel" minOccurs="0"/>
    </xs:sequence>
</xs:complexType>

<xs:complexType name="Playlist">
    <xs:sequence>
        <xs:element name="Path" type="xs:string"/>
        <xs:element name="Shuffle" type="xs:boolean"/>
        <xs:element name="Fader" type="Fader" minOccurs="0"/>
    </xs:sequence>
</xs:complexType>

<xs:complexType name="IntermediatePlaylist">
    <xs:sequence>
        <xs:element name="Path" type="xs:string"/>
        <xs:element name="Shuffle" type="xs:boolean"/>
        <xs:element name="Fader" type="Fader" minOccurs="0"/>
        <xs:element name="SchedIntervalMins" type="xs:positiveInteger"/>
        <xs:element name="NumSchedItems" type="xs:positiveInteger"/>
    </xs:sequence>
    <xs:attribute name="Name" type="xs:string" use="required"/>
</xs:complexType>

<xs:element name="Zone">
    <xs:complexType>
        <xs:sequence>
            <xs:element name="Maintainer" type="xs:string" minOccurs="0"/>
            <xs:element name="Description" type="xs:string" minOccurs="0"/>
            <xs:element name="Comment" type="xs:string" minOccurs="0"/>
            <xs:element name="Main" type="Playlist"/>
            <xs:element name="Fallback" type="Playlist" minOccurs="0"/>
            <xs:element name="Intermediate" type="IntermediatePlaylist" minOccurs="0" maxOccurs="4"/>
        </xs:sequence>
        <xs:attribute name="Name" type="xs:string" use="required"/>
        <xs:attribute name="Start" type="xs:time" use="required"/>
    </xs:complexType>
</xs:element>


<xs:complexType name="Day">
    <xs:sequence>
        <xs:element ref="Zone" maxOccurs="unbounded"/>
    </xs:sequence>
</xs:complexType>

<xs:element name="WeekSchedule">
    <xs:complexType>
        <xs:sequence>
            <xs:element name="Mon" type="Day"/>
            <xs:element name="Tue" type="Day"/>
            <xs:element name="Wed" type="Day"/>
            <xs:element name="Thu" type="Day"/>
            <xs:element name="Fri" type="Day"/>
            <xs:element name="Sat" type="Day"/>
            <xs:element name="Sun" type="Day"/>
        </xs:sequence>
    </xs:complexType>
</xs:element>

</xs:schema>
"""
