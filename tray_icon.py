# TRAY ICON IMPLEMENTATION (https://stackoverflow.com/a/48401917/14113019)

# <<< IMPORTS AND CONFIGURATION >>>

import wx
import wx.adv
from threading import Thread

wx.DisableAsserts()  # to disable wxWidgets Debug Alert due to application exit initiating from another thread


def create_menu_item(menu, label, func):
    """
    Creates a menu item with the specified label and binds it to the given function.

    :param menu: The menu to which the item will be added.
    :param label: The label text of the menu item.
    :param func: The function to be called when the menu item is selected.
    :return: The created menu item.
    """

    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)

    return item


class _TrayIcon(wx.adv.TaskBarIcon):
    def __init__(self, name: str, icon: str, menus: tuple, left_click_action, include_quit):
        super(_TrayIcon, self).__init__()
        self.name = name
        self.menus = menus
        self.left_click_action = left_click_action
        self.include_quit = include_quit

        self.set_icon(icon)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

    def CreatePopupMenu(self):
        """
        Creates and returns the context menu for the tray icon.

        :return: The created wx.Menu.
        """

        menu = wx.Menu()
        for index, menu_data in enumerate(self.menus):
            create_menu_item(menu, menu_data["name"], menu_data["action"])

            if index != len(self.menus) - 1:
                menu.AppendSeparator()

        if self.include_quit:
            if len(self.menus) != 0:
                menu.AppendSeparator()

            create_menu_item(menu, "Quit", self.on_exit)

        return menu

    def set_icon(self, path):
        """
        Sets the icon image for the tray icon.

        :param path: The path to the icon image file.
        """

        icon = wx.Icon(path)
        self.SetIcon(icon, self.name)

    def on_left_down(self, event):  # NOQA
        """
        Handles left-click events on the tray icon.

        :param event: The wx.EVT_TASKBAR_LEFT_DOWN event.
        """

        if self.left_click_action is None:
            return

        self.left_click_action()

    def on_exit(self, event):  # NOQA
        """
        Handles the 'Quit' menu item.

        :param event: The wx.EVT_MENU event.
        """

        wx.CallAfter(self.Destroy)


class _TrayIconApp(wx.App):
    def __init__(self, name: str, icon: str, menus: tuple, left_click_action, include_quit):
        self.name = name
        self.icon = icon
        self.menus = menus
        self.left_click_action = left_click_action
        self.include_quit = include_quit

        super().__init__()

    def OnInit(self):
        """
        Initializes the wxPython application.

        :return: True to indicate a successful initialization.
        """

        _TrayIcon(self.name, self.icon, self.menus, self.left_click_action, self.include_quit)
        return True


class TrayIconApp:
    def __init__(self, name: str, icon: str, menus: tuple, left_click_action=None, include_quit=False):
        self.name = name
        self.icon = icon
        self.menus = menus
        self.left_click_action = left_click_action
        self.include_quit = include_quit

        self.app = None

    def run(self):
        """
        Runs the tray icon application.
        """

        self.app = _TrayIconApp(self.name, self.icon, self.menus, self.left_click_action, self.include_quit)
        self.app.MainLoop()

    def run_detached(self, daemon=False):
        """
        Runs the tray icon application in a separate thread.

        :param daemon: Whether the thread should be a daemon thread (optional).
        """

        Thread(target=self.run, daemon=daemon).start()
