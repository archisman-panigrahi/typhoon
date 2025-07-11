### Generate a python window with gtk4 that can be closed and minimized with two buttons. There should not be any titlebar or window decorations.
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk 
class Window(Gtk.Window):
    def __init__(self, app):
        super().__init__(application=app, title="Custom Window")
        self.set_default_size(400, 300)
        self.set_decorated(False)  # Remove titlebar and decorations

        # Create a vertical box to hold buttons
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_child(vbox)

        # Create close button
        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", self.on_close_clicked)
        vbox.append(close_button)

        # Create minimize button
        minimize_button = Gtk.Button(label="Minimize")
        minimize_button.connect("clicked", self.on_minimize_clicked)
        vbox.append(minimize_button)

        # Create opacity slider
        opacity_adjustment = Gtk.Adjustment(value=1.0, lower=0.2, upper=1.0, step_increment=0.01)
        opacity_slider = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=opacity_adjustment)
        opacity_slider.set_value_pos(Gtk.PositionType.RIGHT)
        opacity_slider.set_digits(2)
        opacity_slider.set_hexpand(True)
        opacity_slider.connect("value-changed", self.on_opacity_changed)
        vbox.append(opacity_slider)

    def on_close_clicked(self, widget):
        self.close()

    def on_minimize_clicked(self, widget):
        surface = self.get_surface()
        if surface is not None:
            surface.minimize()

    def on_opacity_changed(self, slider):
        value = slider.get_value()
        self.set_opacity(value)

class MyApp(Gtk.Application):
    def __init__(self):
        super().__init__()

    def do_activate(self):
        win = Window(self)
        win.present()

if __name__ == "__main__":
    app = MyApp()
    app.run()