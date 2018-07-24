"""
Flow Dashboard - A flow schedule and zone management app

Main function

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

from controller import Controller


if __name__ == '__main__':
    """ Start the controller.

    It subclasses Application.
    """
    Controller().run()
