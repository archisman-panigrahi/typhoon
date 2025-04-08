import dbus
import dbus.service
import dbus.mainloop.glib

from gi.repository import GObject

class Service(dbus.service.Object):
   def __init__(self, message):
      self._message = message

   def run(self):
      dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
      bus_name = dbus.service.BusName("com.example.service", dbus.SessionBus())
      dbus.service.Object.__init__(self, bus_name, "/com/example/service")        

      self._loop = GObject.MainLoop()
      #GObject.idle_add(lambda: self.Update("application://firefox.desktop", {"progress-visible": True, "progress": .9}))
      GObject.idle_add(lambda: self.Update("application://typhoon.desktop", {"count-visible": True, "count": dbus.Int64(10)}))

      self._loop.run()
   
   @dbus.service.signal(dbus_interface="com.canonical.Unity.LauncherEntry", signature='sa{sv}')
   def Update(self, app_uri, properties):
        print(app_uri, properties)

if __name__ == "__main__":
   Service("This is the service").run()
