# <<< IMPORTS >>>

# Kivy usual imports
from kivy.app import App
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.metrics import dp

# Kivy UI related imports
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.relativelayout import RelativeLayout


# <<< CUSTOMIZED WIDGETS >>>

class IconButton(ButtonBehavior, Image):
    """
    Icon which works as a button.
    """

    img_src = StringProperty("")


class EventCard(RelativeLayout):
    """
    Event card which contains image, title, count and next reminder timing corresponding to the event.
    """

    img_src = StringProperty("")
    event_title = StringProperty("")
    event_count = StringProperty("")
    event_timing = StringProperty("")


class CustomToggleButton(ToggleButton):
    """
    `At least one enabled` Toggle Button with custom styling.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    def on_press(self) -> None:
        if self.state == "normal":
            self.state = "down"

    def on_release(self) -> None:
        if self.state == "down":
            self.app.settings_store[self.parent.group] = {"value": self.text}

        if self.parent.action is not None:
            self.parent.action()


class ToggleButtonContainer(BoxLayout):
    """
    Container to store group of custom toggle buttons.
    """

    max_width = NumericProperty()
    toggle_options = ListProperty([])
    group = StringProperty("")
    action = None

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    def add_toggle_buttons(self) -> None:
        """
        Adds toggle buttons to the container, representing options in a toggle group.

        | Note:
        - Clears existing widgets from the container to prevent duplication.
        - Calculates the width for each toggle button based on the maximum width and spacing.
        - Creates a CustomToggleButton for each option in the toggle group.
        - Sets the width, group, and initial state of each toggle button based on application settings.
        - Adds the toggle buttons to the container.
        """

        self.clear_widgets()
        if self.max_width == 0:
            self.max_width = self.width

        for option in self.toggle_options:
            toggle_button = CustomToggleButton(
                text=option,
                width=(self.max_width - dp(self.spacing) * (len(self.toggle_options) - 1)) / len(self.toggle_options),
                group=self.group,
                state="down" if self.app.settings_store[self.group]["value"] == option else "normal"
            )
            self.add_widget(toggle_button)


class SettingBox(BoxLayout):
    """
    Container that contains heading and widgets related to a setting.
    """

    heading = StringProperty("")
