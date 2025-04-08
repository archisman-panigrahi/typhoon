try:
    from PyQt5.QtDBus import QDBusMessage, QDBusConnection
    from PyQt5.QtCore import QVariant

    def send_dbus_message():
        # Create a D-Bus signal message
        message = QDBusMessage.createSignal(
            "/com/example/MyApp",
            "com.canonical.Unity.LauncherEntry",
            "Update"
        )

        # You don't always have to specify all parameters, just the ones you want to update
        properties = {
            "progress-visible": False,  # Enable the progress
            "progress": 0.8,            # Set the progress value (from 0.0 to 1.0)
            "count-visible": True,     # Display the "counter badge"
            "count": 0                  # Set the counter value
        }

        # Add the application desktop file and properties to the message
        message << "application://typhoon.desktop" << QVariant(properties)

        # Send the message over the session bus
        QDBusConnection.sessionBus().send(message)

except ImportError:
    import dbus

    def send_dbus_message():
        # Fallback to dbus if PyQt5 is not available
        try:
            # Connect to the session bus
            bus = dbus.SessionBus()

            # Create a signal message
            obj = bus.get_object("org.freedesktop.DBus", "/com/example/MyApp")
            iface = dbus.Interface(obj, "com.canonical.Unity.LauncherEntry")

            # Prepare the properties
            properties = {
                "progress-visible": False,  # Enable the progress
                "progress": 0.8,            # Set the progress value (from 0.0 to 1.0)
                "count-visible": True,     # Display the "counter badge"
                "count": 0                  # Set the counter value
            }

            # Send the signal
            iface.Update("application://typhoon.desktop", properties)
        except dbus.DBusException as e:
            print(f"Failed to send D-Bus message: {e}")

# Call the function to send the D-Bus message
send_dbus_message()