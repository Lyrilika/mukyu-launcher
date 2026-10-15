import logging
import os
from gi.repository import Gio, GLib

PATH = '/org/mpris/MediaPlayer2'
ROOT = 'org.mpris.MediaPlayer2'
PLAYER = ROOT + '.Player'
TYPES = {
    'PlaybackStatus': 's', 'LoopStatus': 's', 'Rate': 'd', 'Shuffle': 'b',
    'Metadata': 'a{sv}', 'Volume': 'd', 'Position': 'x', 'MinimumRate': 'd',
    'MaximumRate': 'd', 'CanGoNext': 'b', 'CanGoPrevious': 'b', 'CanPlay': 'b',
    'CanPause': 'b', 'CanSeek': 'b', 'CanControl': 'b',
}
WRITABLE = {'LoopStatus', 'Rate', 'Shuffle', 'Volume'}
XML = '<node><interface name="' + ROOT + '">' + '''
<method name="Raise"/><method name="Quit"/>
<property name="CanQuit" type="b" access="read"/>
<property name="CanRaise" type="b" access="read"/>
<property name="HasTrackList" type="b" access="read"/>
<property name="Identity" type="s" access="read"/>
<property name="DesktopEntry" type="s" access="read"/>
<property name="SupportedUriSchemes" type="as" access="read"/>
<property name="SupportedMimeTypes" type="as" access="read"/>
</interface><interface name="''' + PLAYER + '">' + ''.join(
    '<method name="' + name + '"/>' for name in ('Next', 'Previous', 'Pause', 'PlayPause', 'Stop', 'Play')) + '''
<method name="Seek"><arg name="Offset" type="x" direction="in"/></method>
<method name="SetPosition"><arg name="TrackId" type="o" direction="in"/><arg name="Position" type="x" direction="in"/></method>
<method name="OpenUri"><arg name="Uri" type="s" direction="in"/></method>
<signal name="Seeked"><arg name="Position" type="x"/></signal>
''' + ''.join('<property name="' + key + '" type="' + value + '" access="' +
    ('readwrite' if key in WRITABLE else 'read') + '"/>' for key, value in TYPES.items()) + '</interface></node>'


class MprisMedia:
    def __init__(self, controller):
        self.controller = controller
        self.connection = None
        self.registrations = []
        self.last = {}
        self.closed = False
        self.name = ROOT + '.mukyulauncher'
        self.fallback_owner = 0
        self.node = Gio.DBusNodeInfo.new_for_xml(XML)
        self.owner = Gio.bus_own_name(Gio.BusType.SESSION, self.name,
            Gio.BusNameOwnerFlags.DO_NOT_QUEUE, self._bus_acquired, None, self._name_lost)

    def _bus_acquired(self, connection, _name):
        if self.closed:
            return
        self.connection = connection
        self.registrations = [connection.register_object(PATH, interface,
            self._method, self._get, self._set) for interface in self.node.interfaces]
        self.last = {}
        self.update(self.controller.snapshot())

    def _name_lost(self, connection, _name):
        if not self.closed and connection is not None and not self.fallback_owner:
            self.name = ROOT + '.mukyulauncher.instance' + str(os.getpid())
            self.fallback_owner = Gio.bus_own_name_on_connection(connection, self.name,
                Gio.BusNameOwnerFlags.DO_NOT_QUEUE, None, None)

    def _values(self, state):
        metadata = {}
        if state['track_id']:
            metadata = {
                'mpris:trackid': GLib.Variant('o', state['track_id']),
                'xesam:title': GLib.Variant('s', state['title']),
                'xesam:artist': GLib.Variant('as', [state['artist']] if state['artist'] else []),
                'xesam:album': GLib.Variant('s', state['album']),
            }
            if state['duration']:
                metadata['mpris:length'] = GLib.Variant('x', state['duration'])
            if state['art']:
                metadata['mpris:artUrl'] = GLib.Variant('s', state['art'])
        return {
            'PlaybackStatus': state['status'], 'LoopStatus': state['loop'],
            'Rate': 1.0, 'Shuffle': state['shuffle'], 'Metadata': metadata,
            'Volume': state['volume'], 'MinimumRate': 1.0, 'MaximumRate': 1.0,
            'CanGoNext': state['can_next'], 'CanGoPrevious': state['can_previous'],
            'CanPlay': state['can_play'], 'CanPause': state['can_pause'],
            'CanSeek': state['can_seek'], 'CanControl': True,
        }

    def _get(self, _connection, _sender, _path, interface, prop):
        if interface == ROOT:
            values = {
                'CanQuit': ('b', True), 'CanRaise': ('b', True),
                'HasTrackList': ('b', False), 'Identity': ('s', 'Mukyu Launcher'),
                'DesktopEntry': ('s', 'mukyulauncher'),
                'SupportedUriSchemes': ('as', []), 'SupportedMimeTypes': ('as', []),
            }
            return GLib.Variant(*values[prop])
        if prop == 'Position':
            return GLib.Variant('x', self.controller.position())
        return GLib.Variant(TYPES[prop], self._values(self.controller.snapshot())[prop])

    def _set(self, _connection, _sender, _path, interface, prop, value):
        if interface != PLAYER or prop not in WRITABLE:
            return False
        raw = value.unpack()
        if prop == 'Rate':
            if raw == 0.0:
                self.controller.command('Pause')
                return True
            return raw == 1.0
        if prop == 'LoopStatus' and raw not in ('None', 'Track', 'Playlist'):
            return False
        try:
            self.controller.command(prop, raw)
            return True
        except (ValueError, TypeError):
            return False

    def _method(self, _connection, _sender, _path, _interface, name, parameters, invocation):
        if name == 'OpenUri':
            invocation.return_dbus_error('org.freedesktop.DBus.Error.NotSupported', 'Open a track in Mukyu Launcher')
            return
        try:
            args = parameters.unpack()
            self.controller.command(name, args if name == 'SetPosition' else args[0] if args else None)
            invocation.return_value(GLib.Variant('()', ()))
        except Exception as exc:
            logging.getLogger(__name__).exception('MPRIS command failed')
            invocation.return_dbus_error('org.freedesktop.DBus.Error.Failed', str(exc))

    def update(self, state):
        values = {key: GLib.Variant(TYPES[key], value) for key, value in self._values(state).items()}
        changed = {key: value for key, value in values.items()
                   if key != 'CanControl' and (key not in self.last or not value.equal(self.last[key]))}
        self.last = values
        if changed and self.connection is not None and not self.closed:
            self.connection.emit_signal(None, PATH, 'org.freedesktop.DBus.Properties',
                'PropertiesChanged', GLib.Variant('(sa{sv}as)', (PLAYER, changed, [])))

    def seeked(self, position):
        if self.connection is not None and not self.closed:
            self.connection.emit_signal(None, PATH, PLAYER, 'Seeked', GLib.Variant('(x)', (position,)))

    def close(self):
        if self.closed:
            return
        self.closed = True
        for owner in (self.owner, self.fallback_owner):
            if owner:
                Gio.bus_unown_name(owner)
        if self.connection is not None:
            for registration in self.registrations:
                self.connection.unregister_object(registration)
        self.registrations.clear()
        self.connection = None
