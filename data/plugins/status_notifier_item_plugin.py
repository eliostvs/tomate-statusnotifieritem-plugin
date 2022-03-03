import logging
import os

import dbus
import dbus.service
import tomate.pomodoro.plugin as plugin
from tomate.pomodoro import Events, on, Bus, suppress_errors, TimerPayload
from tomate.ui import Systray
from wiring import Graph

logger = logging.getLogger(__name__)


class StatusNotifierItemPlugin(plugin.Plugin):
    @suppress_errors
    def __init__(self):
        super().__init__()
        self.status_item = None
        self.dbus_menu = None
        self.session = None

    def configure(self, bus: Bus, graph: Graph) -> None:
        super().configure(bus, graph)

        self.session = graph.get("tomate.session")
        self.status_item = StatusNotifierItem(graph.get("dbus.session"))
        self.dbus_menu = DbusMenu(graph.get("dbus.session"), graph.get("tomate.ui.view"))

    @suppress_errors
    def activate(self):
        logger.debug("action=activate")
        super().activate()

        self.graph.register_instance(Systray, self)
        if self.session.is_running():
            self.change_status(StatusNotifierItemStatus.Active)

    @suppress_errors
    def deactivate(self):
        logger.debug("action=deactivate")

        self.change_status(StatusNotifierItemStatus.Passive)
        super().deactivate()

    @suppress_errors
    @on(Events.SESSION_START)
    def on_session_start(self, *_, **__):
        logger.debug("action=on-session-start")

        self.change_status(StatusNotifierItemStatus.Active)
        self.change_visibility(True)

    @suppress_errors
    @on(Events.SESSION_INTERRUPT, Events.SESSION_END)
    def on_session_stop(self, *_, **__):
        logger.debug("action=on-session-stop")

        self.change_status(StatusNotifierItemStatus.Passive)

    @suppress_errors
    @on(Events.TIMER_UPDATE)
    def on_timer_update(self, payload: TimerPayload) -> None:
        logger.debug("action=on-timer-update payload=%s", payload)

        self.change_icon(self.icon_name(payload.elapsed_percent))

    @on(Events.WINDOW_SHOW)
    def on_window_show(self, **__):
        logger.debug("action=on-window-show")

        self.change_visibility(True)

    @on(Events.WINDOW_HIDE)
    def on_window_hide(self, **__):
        logger.debug("action=on-window-hide")

        self.change_visibility(False)

    def change_icon(self, new_icon):
        if self.is_activated:
            self.status_item.change_icon(new_icon)

    def change_status(self, new_status):
        if self.is_activated:
            self.status_item.change_status(new_status)

    def change_visibility(self, view_is_visible):
        if self.is_activated:
            self.dbus_menu.update_menu(view_is_visible)

    @staticmethod
    def icon_name(percent):
        return "tomate-{:02.0f}".format(percent)


# https://freedesktop.org/wiki/Specifications/StatusNotifierItem/StatusNotifierItem/


class StatusNotifierItemStatus:
    """
     Describes the status of this item or of the associated application.

     Attributes:
     ----------
    Passive:
         The item doesn't convey important information to the user, it can be considered an "idle" status and is
         likely that visualizations will choose to hide it.
     Active:
         The item is active, is more important that the item will be shown in some way to the user.
     NeedsAttention:
         The item carries really important information for the user, such as battery charge running out
         and is wants to incentive the direct user intervention. Visualizations should emphasize in some way the items
         with NeedsAttention status.
    """

    Passive = "Passive"
    Active = "Active"
    NeedsAttention: "NeedsAttention"


class StatusNotifierItemCategory:
    """
    Describes the category of this item.

    Attributes:
    ----------
    ApplicationStatus:
        The item describes the status of a generic application, for instance the current state of a media player.
        In the case where the category of the item can not be known, such as when the item is being proxied from another
        incompatible or emulated system, ApplicationStatus can be used a sensible default fallback.
    Communications:
        The item describes the status of communication oriented applications, like an instant messenger or an email client.
    SystemServices:
        The item describes services of the system not seen as a standalone application by the user, such as an indicator
        for the activity of a disk indexing service.
    Hardware:
        The item describes the state and control of a particular hardware, such as an indicator of the battery charge or
        sound card volume control.
    """

    ApplicationStatus = "ApplicationStatus"
    Communications = "Communications"
    SystemServices = "SystemServices"
    Hardware = "Hardware"


STATUS_NOTIFIER_ITEM_IFACE = "org.kde.StatusNotifierItem"


class StatusNotifierItem(dbus.service.Object):
    """
    Attributes:
    ---------
    category: str
        Describes the category of this item.
    id: str
        It"s a name that should be unique for this application and consistent between sessions, such as the application
        name itself.
    title: str
        It"s a name that describes the application, it can be more descriptive than id.
    status: StatusNotifierItemStatus
        Describes the status of this item or of the associated application.
    window_id: int
        It"s the windowing-system dependent identifier for a window, the application can choose one of its windows to be
        available through this property or just set 0 if it"s not interested.
    icon_name: str
        The StatusNotifierItem can carry an icon that can be used by the visualization to identify the item.
    icon_pixmap:
        ARGB32 binary representation of the icon.
    overlay_icon_name: str
        The Freedesktop-compliant name of an icon. This can be used by the visualization to indicate extra state
        information, for instance as an overlay for the main icon.
    overlay_icon_pixmap:
        ARGB32 binary representation of the overlay icon.
    attention_icon_name: str
        The Freedesktop-compliant name of an icon. this can be used by the visualization to indicate that the item is in
        RequestingAttention state.
    attention_icon_pixmap:
        ARGB32 binary representation of the attention icon.
    attention_movie_name: str
        An item can also specify an animation associated to the RequestingAttention state.
        This should be either a Freedesktop-compliant icon name or a full path.
        The visualization can choose between the movie or attention_icon_pixmap at its discretion.
    tool_tip:
         Data structure that describes extra information associated to this item, that can be visualized for instance by
          a tooltip
    item_is_menu: boolean
        The item only support the context menu, the visualization should prefer showing the menu or sending ContextMenu()
        instead of Activate()
    menu: dbus.object_path
        DBus path to an object which should implement the com.canonical.dbusmenu interface
    """

    OBJECT_PATH = "/StatusNotifierItem"

    def __init__(self, dbus_session):
        bus_name = dbus.service.BusName(self.object_path, bus=dbus_session)
        dbus.service.Object.__init__(self, bus_name, self.OBJECT_PATH)

        self.category = StatusNotifierItemCategory.ApplicationStatus
        self.status = StatusNotifierItemStatus.Passive
        self.icon_name = "tomate-idle"

        self._dbus_interfaces = {
            STATUS_NOTIFIER_ITEM_IFACE: {
                "AttentionIconName": "tomate-attention",
                "AttentionIconPixmap": dbus.Array(signature="(iiay)"),
                "Category": StatusNotifierItemCategory.ApplicationStatus,
                "IconName": self.icon_name,
                "IconPixmap": dbus.Array(signature="(iiay)"),
                "Id": "tomate",
                "ItemIsMenu": False,
                "Menu": dbus.ObjectPath(DbusMenu.OBJECT_PATH),
                "OverlayIconName": "",
                "OverlayIconPixmap": dbus.Array(signature="(iiay)"),
                "Status": self.status,
                "Title": "Tomate",
                "ToolTip": ("", dbus.Array(signature="(iiay)"), "", ""),
                "WindowId": 0,
            }
        }

        dbus_session.call_blocking(
            "org.kde.StatusNotifierWatcher",
            "/StatusNotifierWatcher",
            "org.kde.StatusNotifierWatcher",
            "RegisterStatusNotifierItem",
            "s",
            (self.object_path,),
        )

    @property
    def object_path(self):
        return "{0}-{1}-1".format(STATUS_NOTIFIER_ITEM_IFACE, os.getpid())

    def change_icon(self, new_icon):
        logger.debug("action=change-icon current-icon=%s new-icon=%s", self.icon_name, new_icon)

        if self.icon_name == new_icon:
            return

        self.icon_name = new_icon
        self.PropertiesChanged(STATUS_NOTIFIER_ITEM_IFACE, {"IconName": self.icon_name}, [])

    def change_status(self, new_status):
        logger.debug("action=change-status current-status=%s new-status=%s", self.status, new_status)

        if self.status == new_status:
            return

        self.status = new_status
        self.PropertiesChanged(STATUS_NOTIFIER_ITEM_IFACE, {"Status": self.status}, [])

    @dbus.service.method(STATUS_NOTIFIER_ITEM_IFACE, in_signature="ii", out_signature="")
    def ContextMenu(self, x, y):
        """
        Asks the status notifier item to show a context menu, this is typically a consequence of user input, such as
        mouse right click over the graphical representation of the item.
        the x and y parameters are in screen coordinates and is to be considered an hint to the item about where to show
        the context menu.
        """
        pass

    @dbus.service.method(STATUS_NOTIFIER_ITEM_IFACE, in_signature="ii", out_signature="")
    def Activate(self, x, y):
        """
        Asks the status notifier item for activation, this is typically a consequence of user input, such as mouse left
        click over the graphical representation of the item.
        The application will perform any task is considered appropriate as an activation request.
        the x and y parameters are in screen coordinates and is to be considered an hint to the item where to show
        eventual windows (if any).
        """
        pass

    @dbus.service.method(STATUS_NOTIFIER_ITEM_IFACE, in_signature="ii", out_signature="")
    def SecondaryActivate(self, x, y):
        """
        Is to be considered a secondary and less important form of activation compared to Activate.
        This is typically a consequence of user input, such as mouse middle click over the graphical representation of
        the item.
        The application will perform any task is considered appropriate as an activation request.
        the x and y parameters are in screen coordinates and is to be considered a hint to the item where to show
        eventual windows (if any).
        """
        pass

    @dbus.service.method(STATUS_NOTIFIER_ITEM_IFACE, in_signature="is", out_signature="")
    def Scroll(self, delta, orientation):
        """
        The user asked for a scroll action. This is caused from input such as mouse wheel over the graphical
        representation of the item.
        The delta parameter represent the amount of scroll, the orientation parameter represent the horizontal or
        vertical orientation of the scroll request and its legal values are horizontal and vertical.
        """
        pass

    @dbus.service.signal(STATUS_NOTIFIER_ITEM_IFACE)
    def NewTitle(self):
        """The item has a new title: the graphical representation should read it again immediately."""
        pass

    @dbus.service.signal(STATUS_NOTIFIER_ITEM_IFACE)
    def NewIcon(self):
        """The item has a new icon: the graphical representation should read it again immediately."""
        pass

    @dbus.service.signal(STATUS_NOTIFIER_ITEM_IFACE)
    def NewAttentionIcon(self):
        """The item has a new attention icon: the graphical representation should read it again immediately."""
        pass

    @dbus.service.signal(STATUS_NOTIFIER_ITEM_IFACE)
    def NewOverlayIcon(self):
        """The item has a new overlay icon: the graphical representation should read it again immediately."""
        pass

    @dbus.service.signal(STATUS_NOTIFIER_ITEM_IFACE)
    def NewToolTip(self):
        """The item has a new tooltip: the graphical representation should read it again immediately."""
        pass

    @dbus.service.signal(STATUS_NOTIFIER_ITEM_IFACE, "s")
    def NewStatus(self, status):
        """The item has a new status, that is passed as an argument of the signal."""
        pass

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface_name, property_name):
        return self._dbus_interfaces.get(interface_name, {}).get(property_name)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface_name):
        return self._dbus_interfaces.get(interface_name, self._dbus_interfaces[STATUS_NOTIFIER_ITEM_IFACE])

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface_name, changed_properties, invalidated_properties):
        pass


# https://github.com/AyatanaIndicators/libdbusmenu/blob/master/libdbusmenu-glib/dbus-menu.xml


class MenuBarStatus:
    """
    Tells if the menus are in a normal state or they believe that they could use some attention.
    Cases for showing them would be if help were referring to them or they accessors were being highlighted.
    Attributes:
    ----------
    normal: str
        in almost all cases
    notice:
        when it should have a higher priority to be show
    """

    Normal = "normal"
    Notice = "notice"


DBUSMENU_IFACE = "com.canonical.dbusmenu"


class DbusMenuItem:
    """
    Attributes:
    ----------
    type: str
        Can be one be "standard", an item which can be clicked to trigger an action or show another menu, or "separator"
    label : str
        Text of the item
    enabled: boolean
        Whether the item can be activated or not
    visible: boolean
        True if the item is visible in the menu
    icon-name: str
        Icon name of the item, following the freedesktop.org icon spec
    icon-data:
        PNG data of the icon
    shortcut:
        The shortcut of the item. Each array represents the key press in the list of keypresses.
        Each list of strings contains a list of modifiers and then the key that is used.
        The modifier strings allowed are: "Control", "Alt", "Shift" and "Super".
        A simple shortcut like Ctrl+S is represented as: [["Control", "S"]].
        A complex shortcut like Ctrl+Q, Alt+X is represented as: [["Control", "Q"], ["Alt", "X"]]
    toggle-type: str
        If the item can be toggled, this property should be set to "checkmark" if Item is an independent togglable item,
        "radio", Item is part of a group where only one item can be toggled at a time, or "", if item cannot be toggled
    toggle-state: int
        Describe the current state of a "togglable" item.
        Can be one of, 0 = off,  1 = on, anything else = indeterminate.
    children-display: str
        If the menu item has children this property should be set to "submenu".
    disposition: str
        How the menuitem feels the information it's displaying to the user should be presented.
        "normal" a standard menu item, "informative" providing additional information to the user, "warning" looking at
        potentially harmful results, or "alert" something bad could potentially happen.
    """

    ATTRIBUTES = [
        "children-display",
        "disposition",
        "enabled",
        "label",
        "toggle-state",
        "toggle-type",
        "type",
        "visible",
    ]


class DbusMenu(dbus.service.Object):
    """
    Attributes:
    ----------
    version:
        Provides the version of the DBusmenu API that this API is implementing.
    status:
        Tells if the menus are in a normal state, or they believe that they could use some attention.
    text_direction: str
        Represents the way the text direction of the application.
        This allows the server to handle mismatches intelligently.
        For left- to-right the string is "ltr" for right-to-left it is "rtl".
    icon_theme_path:
        A list of directories that should be used for finding icons using the icon naming spec.
        Ideally there should only be one for the icon theme, but additional ones are often added by applications for app
        specific icons.
    """

    OBJECT_PATH = "/MenuBar"
    SHOW = 1
    HIDE = 2

    def __init__(self, dbus_session, view):
        dbus.service.Object.__init__(self, dbus_session, self.OBJECT_PATH)
        self.revision = 0
        self.items = {
            0: {
                "children-display": "submenu",
                "disposition": "normal",
                "enabled": True,
                "label": "",
                "toggle-state": -1,
                "toggle-type": "",
                "type": "standard",
                "visible": True,
                "submenu": [1, 2],
            },
            self.SHOW: {
                "children-display": "",
                "disposition": "normal",
                "enabled": True,
                "label": "Show",
                "toggle-state": -1,
                "toggle-type": "",
                "type": "standard",
                "visible": False,
                "clicked": lambda: view.show(),
            },
            self.HIDE: {
                "children-display": "",
                "disposition": "normal",
                "enabled": True,
                "label": "Hide",
                "toggle-state": -1,
                "toggle-type": "",
                "type": "standard",
                "visible": True,
                "clicked": lambda: view.hide(),
            },
        }

        self._dbus_interfaces = {DBUSMENU_IFACE: {"Status": MenuBarStatus.Normal, "TextDirection": "ltr", "Version": 4}}

    def update_menu(self, is_visible):
        logger.debug("action=update-layout view-visible=%d", is_visible)

        self.items[self.SHOW]["visible"] = not is_visible
        self.items[self.HIDE]["visible"] = is_visible
        self.ItemsPropertiesUpdated([(idx, self._render_item(item)) for idx, item in self.items.items()], [])

    @dbus.service.method(DBUSMENU_IFACE, in_signature="iias", out_signature="u(ia{sv}av)")
    def GetLayout(self, parent_id, recursion_depth, property_names=None):
        """
        Provides the layout and properties that are attached to the entries that are in the layout.
        It only gives the items that are children of the item that is specified in @a parentId.
        It will return all the properties or specific ones depending on the value in @a propertyNames.
        The format is recursive, where the second "v" is in the same format as the original "a(ia{sv}av)".
        Its content depends on the value of @a recursionDepth.

        :param parent_id: The ID of the parent node for the layout. For grabbing the layout from the root node use zero.
        :param recursion_depth: The amount of levels of recursion to use.
                                This affects the content of the second variant array.
                                -1: deliver all the items under the @a parentId.
                                0: no recursion, the array will be empty.
                                n: array will contain items up to 'n' level depth.
            :param property_names: The list of item properties we are interested in.
                                   If there are no entries in the list all the properties will be sent.
        :return: The revision number of the layout. For matching with layoutUpdated signals.
                 The layout, as a recursive structure.
        """
        logger.debug(
            "action=get-layout parent-id=%d recursion-depth=%d property-names=%s",
            parent_id,
            recursion_depth,
            property_names,
        )

        return self.revision, (
            parent_id,
            self._render_item(self.items[parent_id], property_names),
            self._render_submenu(self.items, self.items[parent_id], property_names),
        )

    @dbus.service.method(DBUSMENU_IFACE, in_signature="isvu", out_signature="")
    def Event(self, idx, event_id, data, timestamp):
        """
        This is called by the applet to notify the application an event happened on a
        menu item. eventId can be one of the following:
            * "clicked"
            * "hovered"
            * "opened"
            * "closed"
        Vendor specific events can be added by prefixing them with "x-<vendor>-"
        """
        logger.debug("action=event id=%d event_id=%s data=%s", idx, event_id, data)

        self.items[idx].get(event_id, lambda: None)()

    @dbus.service.method(DBUSMENU_IFACE, in_signature="a(isvu)", out_signature="ai")
    def EventGroup(self, events):
        """
        Used to pass a set of events as a single message for possibly several menu items.
        This is done to optimize DBus traffic.
        Should return a list of ids that are not found. events is a list of events in the same format as used for the
        Event method.
        """
        return dbus.Array(signature="i")

    @dbus.service.method(DBUSMENU_IFACE, in_signature="is", out_signature="v")
    def GetProperty(self, idx, name):
        """
        Get a signal property on a single item.  This is not useful if you're going to implement this interface,
        it should only be used if you're debugging via a commandline tool.

        :param idx: the id of the item which received the event
        :param name: the name of the property to get
        :return: the value of the property
        """
        logger.debug("action=get-property id=%d name=%s", idx, name)

        return self.items[idx][name]

    @dbus.service.method(DBUSMENU_IFACE, in_signature="aias", out_signature="a(ia{sv})")
    def GetGroupProperties(self, ids, property_names):
        """
        Returns the list of items which are children of @a parentId.

        :param ids: A list of ids that we should be finding the properties on.
                    If the list is empty, all menu items should be sent.
        :param property_names: The list of item properties we are interested in.
                               If there are no entries in the list all the properties will be sent.
        :return: An array of property values. An item in this area is represented as a struct following this format:
                 id unsigned the item id
                 properties map(string => variant) the requested item properties
        """
        logger.debug("action=get-group-properties ids=%s", ids)

        return [(idx, self._render_item(self.items[idx], property_names)) for idx in ids if idx in self.items.keys()]

    @dbus.service.method(DBUSMENU_IFACE, in_signature="i", out_signature="b")
    def AboutToShow(self, idx):
        """
        This is called by the applet to notify the application that it is about to show the menu under the specified item.

        :param idx: Which menu item represents the parent of the item about to be shown.
        :return: Whether this AboutToShow event should result in the menu being updated.
        """
        logger.debug("action=about-to-show ids=%d", idx)

        return False

    @dbus.service.method(DBUSMENU_IFACE, in_signature="aiai", out_signature="aiai")
    def AboutToShowGroup(self, ids, updates_needed):
        """
        A function to tell several menus being shown that they are about to be shown to the user.
        This is likely only useful for programmatic purposes so while the return values are returned, in general, the
        singular function should be used in most user interaction scenarios.

        :param ids: The IDs of the menu items whose submenus are being shown.
        :param updates_needed: The IDs of the menus that need updates.
        :return: List IDs of the menus that need updates and list of menuitem IDs that couldn't be found
        """
        return dbus.Array(signature="i"), dbus.Array(signature="i")

    @dbus.service.signal(DBUSMENU_IFACE, "a(ia{sv})a(ias)")
    def ItemsPropertiesUpdated(self, update_props, remove_props):
        """
        Triggered when there are lots of property updates across many items, so they all get grouped into a single dbus
        message.
        The format is the ID of the item with a hashtable of names and values for those properties.
        """
        pass

    @dbus.service.signal(DBUSMENU_IFACE, "ui")
    def LayoutUpdated(self, revision, parent):
        """
        Triggered by the application to notify display of a layout update, up to revision

        :param revision: The revision of the layout that we're currently on.
        :param parent: If the layout update is only of a subtree, this is the parent item for the entries that have changed.
            It is zero if the whole layout should be considered invalid.
        """
        pass

    @dbus.service.signal(DBUSMENU_IFACE, "iu")
    def ItemActivationRequested(self, id, timestamp):
        """
        The server is requesting that all clients displaying this menu open it to the user.
        This would be for things like hotkeys that when the user presses them the menu should open and display itself
        to the user.

        :param id: ID of the menu that should be activated.
        :param timestamp: The time that the event occurred.
        """
        pass

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="ss", out_signature="v")
    def Get(self, interface_name, property_name):
        return self._dbus_interfaces.get(interface_name, {}).get(property_name)

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface_name):
        return self._dbus_interfaces.get(interface_name, self._dbus_interfaces[DBUSMENU_IFACE])

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature="sa{sv}as")
    def PropertiesChanged(self, interface_name, changed_properties, invalidated_properties):
        pass

    @staticmethod
    def _render_item(item, properties=None):
        if properties is None or not len(properties):
            properties = DbusMenuItem.ATTRIBUTES

        return dbus.Dictionary({k: item[k] for k in properties}, signature="sv")

    @staticmethod
    def _render_submenu(items, item, properties=None):
        if "submenu" in item:
            return [
                (idx, DbusMenu._render_item(items[idx], properties), dbus.Array([], signature="v"))
                for idx in item["submenu"]
            ]
        else:
            return dbus.Array([], signature="v")
