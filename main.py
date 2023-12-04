# <<< IMPORTS AND CONFIGURATION >>>

# Initial setup
from kivy.config import Config

Config.set("graphics", "resizable", False)  # disable window resizing
Config.set("input", "mouse", "mouse, disable_multitouch")  # disable multitouch emulation (orange dot on right click)

# Setup opening of already running instance of the application if attempt is made to open second instance
from sys import exit
from tendo import singleton
from kivy.storage.dictstore import DictStore
from keyboard import add_hotkey, remove_hotkey, press_and_release

try:
    me = singleton.SingleInstance()
except singleton.SingleInstanceException:
    press_and_release(DictStore("data/settings.dat")["visibility_hotkey"]["value"])
    exit(-1)

# Set default window color and hide it
from kivy.clock import Clock
from kivy.core.window import Window

Window.clearcolor = (24 / 255, 24 / 255, 24 / 255)
Clock.schedule_once(lambda dt: Window.hide(), 0)

# Set default font of the application
from kivy.core.text import LabelBase, DEFAULT_FONT

LabelBase.register(DEFAULT_FONT, "assets/fonts/nunito.ttf")

# Kivy usual imports
from kivy.app import App
from kivy.clock import mainthread
from kivy.core.audio import SoundLoader
from kivy.network.urlrequest import UrlRequest
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty, NumericProperty

# Kivy UI related imports
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from custom_widgets import IconButton, EventCard, CustomToggleButton, ToggleButtonContainer, SettingBox  # NOQA

# Miscellaneous imports
from csv import writer
from os import makedirs
from os.path import join
from random import choice
from tray_icon import TrayIconApp
from helpers import format_time, notify
from datetime import datetime, timedelta


# <<< SCREENS AND SCREEN MANAGER >>>

class HomeScreen(Screen):
    quote = ObjectProperty()
    welcome_text = ObjectProperty()
    screen_time = ObjectProperty()
    eyes_event_card = ObjectProperty()
    water_event_card = ObjectProperty()
    exercise_event_card = ObjectProperty()

    greets = {
        "morning": [
            "Rise and shine!",
            "The early bird catches the worm.",
            "Welcome to a brand new day!"
        ],
        "afternoon": [
            "Halfway through the day, keep it up!",
            "How's your day going so far?",
            "Afternoon vibes are in full swing!"
        ],
        "evening": [
            "The stars are out, and so are you.",
            "Twilight welcomes you with open arms.",
            "Let the moonlight guide your path."
        ],
        "midnight": [
            "Night owls unite!",
            "Burning the midnight oil, I see.",
            "Ready for some moonlight magic?"
        ]
    }

    def __init__(self) -> None:
        super().__init__(name="Home Screen")
        self.app = App.get_running_app()

        # Set initial quote from the saved quotes
        self.set_quote_text(None, choice(self.app.quotes_store["quotes"]["quotes"]))

        # Store last hour in which user was greeted and try to update greeting every second
        self.greet_hour = datetime.now().hour
        Clock.schedule_interval(lambda dt: self.update_welcome_text(), 1)

        # Set initial screen time fetched from database without incrementing the value and
        # schedule increment every minute
        self.update_screen_time(False)
        Clock.schedule_interval(lambda dt: self.update_screen_time(), 60)

        self.event_card_mappings = {  # to access event cards using event types/names
            "eyes": self.eyes_event_card,
            "water": self.water_event_card,
            "exercise": self.exercise_event_card
        }

        # Set event count for each event fetched from database
        self.update_event_count_text("eyes")
        self.update_event_count_text("water")
        self.update_event_count_text("exercise")

    def get_greeting(self, name: str) -> str:
        """
        Returns a greeting based on the time of day and the provided name.

        :param name: The name for which the greeting is addressed.
        :return: A greeting message based on the time of day and the provided name.
        """

        self.greet_hour = datetime.now().hour

        if name:
            hello_text = f"Hello, {name.title()}!"
        else:
            hello_text = "Hello!"

        if self.greet_hour > 17:
            return f"{hello_text} {choice(self.greets['evening'])}"
        elif self.greet_hour > 12:
            return f"{hello_text} {choice(self.greets['afternoon'])}"
        elif self.greet_hour > 6:
            return f"{hello_text} {choice(self.greets['morning'])}"
        else:
            return f"{hello_text} {choice(self.greets['midnight'])}"

    def update_welcome_text(self, force_update: bool = False) -> None:
        """
        Updates the welcome text based on the current time.

        Note: The welcome text is updated only if the current hour is different from the last known hour,
        or if `force_update` is set to True.

        :param force_update: If True, forces an update of the welcome text regardless of the time. Defaults to False.
        """

        new_greet_hour = datetime.now().hour != self.greet_hour

        if force_update or new_greet_hour:
            new_name = self.app.settings_store["user_name"]["value"].lower()
            self.welcome_text.text = self.get_greeting(new_name)

    def toggle_app_status(self):
        """
        Toggles the running status of the application.

        | Note:
        - Toggles the `running` attribute of the application.
        - Retrieves the "Reminder Screen" and its associated objects.
        - If the application is paused, clears reminder timings and cancels the reminder event.
        - If the application is resumed, sets new reminders and schedules the reminder interval.
        """

        self.app.running = not self.app.running

        reminder_screen = self.app.screen_manager.get_screen("Reminder Screen")
        if not self.app.running:
            reminder_screen.reminder_timings.clear()
            reminder_screen.remind_event.cancel()
        else:
            reminder_screen.set_reminders()
            reminder_screen.schedule_remind_interval()

    def update_quote_db(self, quote_data: dict) -> None:
        """
        Updates a quote database with new quote data.

        Note: If the provided quote is not already in the database, it is added to the list of quotes.

        :param quote_data: A dictionary containing quote information.
        """

        new_quote = {"content": quote_data["content"], "author": quote_data["author"]}
        if new_quote not in self.app.quotes_store["quotes"]["quotes"]:
            quotes = self.app.quotes_store["quotes"]["quotes"]
            quotes.append(new_quote)
            self.app.quotes_store["quotes"] = {"quotes": quotes}

    def set_quote_text(self, req, res: dict) -> None:
        """
        Sets the text of quote widget based on the response data.

        Note: If a request is provided (not None), it means the quote is fetched from the API hence the quote database
        is updated with the response data.

        :param req: The request data, which is optional.
        :param res: A dictionary containing quote information.
        """

        self.quote.text = f"\"{res['content']}\"\n{' ' * 80}~ {res['author']}"
        self.quote.texture_update()

        if req is not None:
            self.update_quote_db(res)

    def get_quote(self) -> None:
        """
        Requests a quote using the quotable API and updates the text of the quote widget with the retrieved quote.
        """

        UrlRequest("https://api.quotable.io/random", self.set_quote_text)

    def update_screen_time(self, increment: bool = True) -> None:
        """
        Updates the screen time information and change the text of screen_time widget.

        | Note:
        - The screen time is tracked on a per-day basis.
        - If the screen time history for the current day does not exist, it is initialized with zero minutes.
        - If increment is True, the screen time for the current day is incremented by 1 minute.
        - The updated screen time is displayed on the screen.

        :param increment: If True, increments the screen time; otherwise, keeps it unchanged. Defaults to True.
        """

        today = str(datetime.now().date())

        if not self.app.screen_time_history.exists(today):
            self.app.screen_time_history[today] = {"minutes": 0}
        if increment:
            prev_minutes = self.app.screen_time_history[today]["minutes"]
            self.app.screen_time_history[today] = {"minutes": prev_minutes + 1}

        curr_minutes = self.app.screen_time_history[today]["minutes"]
        screen_time_text = "Screen time: " + format_time(curr_minutes)

        self.screen_time.text = screen_time_text
        self.screen_time.texture_update()

    def set_reminders_text(self, reminder_timings: dict = None) -> None:
        """
        Sets the timing for reminders based on the provided or "Reminder Screen" reminder timings.

        | Note:
        - If reminder_timings is None, it uses the timings from the "Reminder Screen" in the app.
        - The time format is determined by the user's settings (AM/PM or 24-hour format).
        - The formatted reminder timings are assigned to respective event text properties.

        :param reminder_timings: A dictionary containing reminder timings for different events. Defaults to None.
        """

        if reminder_timings is None:
            reminder_timings = self.app.screen_manager.get_screen("Reminder Screen").reminder_timings

        time_format = "%I:%M %p" if self.app.settings_store["time_format"]["value"] == "AM/PM" else "%H:%M"
        str_timings = {}
        for event_type in reminder_timings:
            str_timings[event_type] = reminder_timings[event_type].strftime(time_format)

        self.eyes_event_card.event_timing = f"Next reminder: {str_timings['eyes']}"
        self.water_event_card.event_timing = f"Next reminder: {str_timings['water']}"
        self.exercise_event_card.event_timing = f"Next reminder: {str_timings['exercise']}"

    def update_event_count_db(self, event_type: str) -> None:
        """
        Updates the event count history in the database based on the specified event type.

        | Note:
        - The event count history is tracked on a per-day basis.
        - The count for the specified event type is incremented by 1.
        - For the water reminder, both the count and total water intake are updated.
        - The corresponding event count text is updated to reflect the changes.

        :param event_type: The type of the event for which the count is to be updated.
        """

        event_card = self.event_card_mappings[event_type]
        today = str(datetime.now().date())

        if not self.app.event_count_history.exists(today):
            self.app.event_count_history[today] = {"eyes": 0, "water": [0, 0], "exercise": 0}

        event_counts = self.app.event_count_history[today]
        prev_count = event_counts[event_type]

        if event_card.event_title != "Drank water":
            event_counts[event_type] = prev_count + 1
            self.app.event_count_history[today] = event_counts
        else:
            event_counts["water"][0] += 1

            water_intake = self.app.settings_store["water_intake"]["value"]
            if water_intake:
                event_counts["water"][1] += int(water_intake)

            self.app.event_count_history[today] = event_counts

        self.update_event_count_text(event_type)

    def update_event_count_text(self, event_type: str) -> None:
        """
        Updates the text displaying the count for a specific event type.

        | Note:
        - The event count text is updated based on the count history for the current day.
        - In case of water reminder, the text is updated based on the state of water intake tracker.
        - The updated event count text is reflected in the corresponding event widget.

        :param event_type: The type of the event for which the count text is to be updated.
        """

        event_card = self.event_card_mappings[event_type]
        today = str(datetime.now().date())

        if not self.app.event_count_history.exists(today):
            self.app.event_count_history[today] = {"eyes": 0, "water": [0, 0], "exercise": 0}

        count = self.app.event_count_history[today][event_type]

        if event_card.event_title != "Drank water":
            event_card.event_count = f"{count} times"
            return

        water_intake = self.app.settings_store["water_intake"]["value"]
        if water_intake:
            water_quantity = self.app.event_count_history[today]["water"][1]
            water_quantity = f"{water_quantity / 1000} L" if water_quantity > 1000 else f"{water_quantity} mL"
            event_card.event_count = water_quantity
        else:
            event_card.event_count = f"{count[0]} times"


class ReminderScreen(Screen):
    skip_count = NumericProperty(3)
    reminder_text = ObjectProperty()
    img_src = StringProperty("")
    event_type = StringProperty("")

    freq_mappings = {
        "20 min": 20,
        "30 min": 30,
        "45 min": 45,
        "1 hr": 60,
        "1.5 hr": 90,
        "2 hr": 120
    }

    notification_titles = {
        "eyes": "Eyes Relaxation Reminder",
        "water": "Hydration Reminder",
        "exercise": "Exercise Reminder"
    }

    reminder_texts = {
        "eyes": [
            "Take a break! Relax your eyes and look away from the screen for a minute.",
            "Let your eyes stretch too! Pause and focus on a distant object for a quick refresh.",
            "It's time to refresh your eyes. Close them for a moment and let them rest."
        ],
        "water": [
            "Stay hydrated! Grab your water bottle and take a moment for a drink.",
            "It's water time! Remember to keep yourself hydrated throughout the day.",
            "Water break! Pour yourself a glass and savor the goodness of staying hydrated."
        ],
        "exercise": [
            "Get moving! Stand up, stretch, and take a short walk around.",
            "Exercise break! Do a quick set of stretches or simple exercises to boost your energy.",
            "Time to move! Incorporate some physical activity into your routine for a healthy break."
        ]
    }

    def __init__(self) -> None:
        super().__init__(name="Reminder Screen")
        self.app = App.get_running_app()
        self.reminder_sound = SoundLoader.load("assets/sounds/reminder_sound.mp3")

        self.frequencies = {
            "eyes": self.freq_mappings[self.app.settings_store["eyes_freq"]["value"]],
            "water": self.freq_mappings[self.app.settings_store["water_freq"]["value"]],
            "exercise": self.freq_mappings[self.app.settings_store["exercise_freq"]["value"]]
        }

        self.reminder_timings = {
            "eyes": None,
            "water": None,
            "exercise": None
        }

        # Set initial reminders on app start and schedule interval to check and remind on the calculated time
        self.set_reminders()
        self.remind_event = None
        self.schedule_remind_interval()

        # Schedule interval to run reset_skip_count method every second so that skip_count resets on new day
        Clock.schedule_interval(lambda dt: self.reset_skip_count(), 1)

    def on_pre_enter(self, *args) -> None:
        self.reminder_sound.play()

    def schedule_remind_interval(self):
        """
        Schedule to run `remind` method every second.
        """

        self.remind_event = Clock.schedule_interval(lambda dt: self.remind(), 1)

    def set_reminders(self) -> None:
        """
        Sets reminder timings for eyes, water, and exercise events.

        | Note:
        - Calls the `set_reminder_timing` method for each event type to set their respective reminder timings.
        - Updates the reminders text on the "Home Screen" using the `set_reminders_text` method.
        """

        self.set_reminder_timing("eyes")
        self.set_reminder_timing("water")
        self.set_reminder_timing("exercise")
        self.app.screen_manager.get_screen("Home Screen").set_reminders_text(self.reminder_timings)

    def set_frequencies(self) -> None:
        """
        Sets frequencies for eyes, water, and exercise events based on user settings.

        | Note:
        - Retrieves frequency values from user settings for each event type.
        - Retrieves integer values of corresponding frequency settings using `freq_mappings`.
        - Assigns the frequencies to the respective events in the `frequencies` dictionary.
        """

        self.frequencies["eyes"] = self.freq_mappings[self.app.settings_store[f"eyes_freq"]["value"]]
        self.frequencies["water"] = self.freq_mappings[self.app.settings_store[f"water_freq"]["value"]]
        self.frequencies["exercise"] = self.freq_mappings[self.app.settings_store[f"exercise_freq"]["value"]]

    def set_reminder_timing(self, event_type: str) -> None:
        """
        Sets the reminder timing for a specific event type.

        | Note:
        - Calculates the reminder timing based on the current time and frequency settings.
        - Iteratively checks for collisions with existing reminder timings.
        - Sets the reminder timing when a non-colliding time is found and exits the loop.

        :param event_type: The type of the event for which the reminder timing is to be set.
        """

        multiplier = 1
        while True:
            timing = (datetime.now().replace(second=0, microsecond=0) +
                      timedelta(minutes=self.frequencies[event_type] * multiplier))
            if timing not in self.reminder_timings.values():
                self.reminder_timings[event_type] = timing
                break

            multiplier += 1

    def remind(self) -> None:
        """
        Triggers reminders for scheduled events.

        | Note:
        - Iterates through each event type in the reminder timings.
        - Checks if the current time matches the scheduled reminder time.
        - If a match is found, updates UI elements and displays the reminder on the "Reminder Screen."
        - Cancels the reminder event to prevent repeated triggering.
        - Shows the application window and notifies the user with a notification.
        """

        for event_type in self.reminder_timings:
            if datetime.now().strftime("%I:%M") == self.reminder_timings[event_type].strftime("%I:%M"):
                self.img_src = f"assets/images/{event_type}.png"
                self.event_type = event_type
                self.reminder_text.text = choice(self.reminder_texts[event_type])
                self.app.screen_manager.current = "Reminder Screen"
                self.remind_event.cancel()  # NOQA
                self.remind_event = None

                self.app.show_app()

                notify(self.notification_titles[event_type], self.reminder_text.text, event_type)
                # self.app.tray_icon.notify(self.reminder_text.text, self.notification_titles[event_type])

    def update_reminders(self) -> None:
        """
        Updates the reminder timings for scheduled events.

        | Note:
        - Iterates through each event type in the reminder timings.
        - Checks if the scheduled reminder time has passed for each event.
        - If the time has passed and the event type is not the current event, updates the reminder timing.
        - Sets the reminder timing for the current event to ensure it continues to trigger.
        - Updates the reminders text on the "Home Screen."
        - Reschedules interval to check and remind on the calculated time
        """

        for event_type in self.reminder_timings:
            if datetime.now() >= self.reminder_timings[event_type] and event_type != self.event_type:
                self.set_reminder_timing(event_type)
        self.set_reminder_timing(self.event_type)
        self.app.screen_manager.get_screen("Home Screen").set_reminders_text(self.reminder_timings)

        self.schedule_remind_interval()

    def handle_reminder_btn_click(self, action: str):
        """
        Handles button clicks on the reminder screen.

        :param action: A string indicating the action to be performed ("done" or "skip").
        """

        self.update_reminders()
        self.app.hide_app()

        if action == "done":
            self.app.screen_manager.get_screen("Home Screen").update_event_count_db(self.event_type)
        elif action == "skip":
            self.skip_count -= 1

    def reset_skip_count(self):
        """
        Resets the daily skip count to the maximum value if new day has started.
        """

        if "00:00:00" in str(datetime.now().time()):
            self.skip_count = 3


class SettingsScreen(Screen):
    name_text_input = ObjectProperty()
    water_intake = ObjectProperty()
    hotkey = ObjectProperty()
    log_save_location = ObjectProperty()
    log_save_btn = ObjectProperty()

    def __init__(self) -> None:
        super().__init__(name="Settings Screen")
        self.app = App.get_running_app()
        self.max_name_length = 20
        self.alphabets = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def update_user_name(self) -> None:
        """
        Updates the user's name in the application settings and refreshes the welcome text.

        | Note:
        - Retrieves the user's name from the text input field.
        - Checks for invalid or excessive input, clearing the input field or truncating the name if necessary.
        - Updates the user's name in the application settings.
        - Triggers the refresh of the welcome text on the "Home Screen."
        """

        user_name = self.name_text_input.text

        if user_name == " ":
            self.name_text_input.text = ""
            return
        elif len(user_name) > self.max_name_length:
            self.name_text_input.text = self.name_text_input.text[:self.max_name_length]

        self.app.settings_store["user_name"] = {"value": user_name}
        self.app.screen_manager.get_screen("Home Screen").update_welcome_text(True)

    def update_hotkey(self) -> None:
        """
        Updates the visibility hotkey for the application.

        | Note:
        - Retrieves the entered hotkey alphabet from the text input field.
        - Checks for valid input (a single alphabet) and clears the input field if invalid.
        - Sets the hint text for the hotkey field with the formatted hotkey combination.
        - Updates the visibility hotkey in the application settings.
        - Removes the current hotkey binding and creates a new one based on the updated settings.
        - Clears the hotkey input field and unfocuses it.
        """

        alphabet = self.hotkey.text.upper()

        if alphabet not in self.alphabets or len(alphabet) > 1:
            self.hotkey.text = ""
            return

        self.hotkey.hint_text = f"Ctrl + Shift + {alphabet}"
        self.app.settings_store["visibility_hotkey"] = {"value": self.hotkey.hint_text}

        remove_hotkey(self.app.hotkey_return_value)
        self.app.create_hotkey()

        self.hotkey.text = ""
        self.hotkey.focus = False

    def update_water_intake(self) -> None:
        """
        Updates the water intake per reminder and refreshes the water event count text.

        Note:
        - Retrieves the water intake value from the input field.
        - Updates the water intake in the application settings.
        - Triggers the refresh of the water event count text on the "Home Screen."
        - If the water intake is cleared, sets the total water intake for the day to zero in the event count history.
        """

        self.app.settings_store["water_intake"] = {"value": self.water_intake.text}
        self.app.screen_manager.get_screen("Home Screen").update_event_count_text("water")

        if self.water_intake.text == "":
            today = str(datetime.now().date())
            event_counts = self.app.event_count_history[today]
            event_counts["water"][1] = 0
            self.app.event_count_history[today] = event_counts

    def reset_log_save_btn_text(self) -> None:
        """
        Reset the text of the reminder logs save button to "Save".
        """

        self.log_save_btn.text = "Save"

    def save_reminder_logs(self) -> None:
        """
        Saves reminder logs to a CSV file based on screen time and event counts.

        | Note:
        - Creates the directory specified in the log save location input field if it doesn't exist.
        - Generates a unique log filename based on the current date and time.
        - Opens the log file in write mode and initializes a CSV writer.
        - Writes headers and log data to the CSV file based on screen time and event counts.
        - Closes the log file after writing and updates the log save button text.
        - Resets the log save button text after a delay of 3 seconds.
        """

        makedirs(self.log_save_location.text, exist_ok=True)
        log_id = str(datetime.now().replace(microsecond=0)).replace(':', '.')
        log_filename = f"Wellbeing Reminder Logs {log_id}.csv"
        log_file = open(join(self.log_save_location.text, log_filename), "w", newline="")
        csv_writer = writer(log_file)
        csv_writer.writerow(("Date", "Screen Time", "Eye Care Count", "Hydration Count", "Water Quantity",
                             "Exercise Count"))

        screen_times = self.app.screen_time_history
        event_counts = self.app.event_count_history

        logs = {}
        for date in screen_times.keys():
            logs[date] = [date, format_time(screen_times[date]["minutes"]), "N/A", "N/A", "N/A", "N/A"]

        for date in event_counts.keys():
            if date not in logs.keys():
                logs[date] = [date, "N/A", "N/A", "N/A", "N/A"]

            logs[date][2] = event_counts[date]["eyes"]
            water_count, water_quantity = event_counts[date]["water"]
            logs[date][3] = water_count
            if water_quantity:
                logs[date][4] = water_quantity
            logs[date][5] = event_counts[date]["exercise"]

        csv_writer.writerows(logs.values())
        log_file.close()

        self.log_save_btn.text = f"Saved {log_filename}"
        Clock.schedule_once(lambda dt: self.reset_log_save_btn_text(), 3)


class CustomScreenManager(ScreenManager):
    def on_touch_down(self, touch) -> bool:
        # Block clicks from right and middle click
        if touch.button in ["right", "middle"]:
            return True

        super().on_touch_down(touch)


# <<< APPLICATION >>>

class WellbeingApp(App):
    running = BooleanProperty(True)

    def __init__(self) -> None:
        super().__init__()
        Window.bind(on_request_close=self.hide_app)  # hide app when closed with "X" button
        self.icon = "assets/images/heart.png"

        self.tray_icon = None
        self.visible = False
        self.hotkey_return_value = None

        self.quotes_store = DictStore("data/quotes.dat")
        self.set_default_quotes()

        self.settings_store = DictStore("data/settings.dat")
        self.set_default_settings()

        self.screen_time_history = DictStore("data/screen_time_history.dat")
        self.event_count_history = DictStore("data/event_count_history.dat")

        self.screen_manager = CustomScreenManager(transition=NoTransition())

    def hide_app(self, *args) -> bool:  # NOQA
        """
        Hides the application window and minimizes it to the system tray.

        :return: True to block app's exit
        """

        self.root_window.minimize()
        self.root_window.hide()

        if self.screen_manager.get_screen("Reminder Screen").remind_event is not None:
            self.screen_manager.current = "Home Screen"
            self.screen_manager.get_screen("Home Screen").get_quote()

        self.visible = False
        return True

    @mainthread
    def close_app(self, *args) -> None:  # NOQA
        """
        Closes the application window.
        """

        self.root_window.close()

    @mainthread
    def show_app(self, *args) -> None:  # NOQA
        """
        Shows the application window.
        """

        self.root_window.show()
        self.visible = True

    @mainthread
    def toggle_app_visibility(self) -> None:
        """
        Toggles the visibility of the application window.
        """

        if self.visible:
            self.hide_app()
        else:
            self.show_app()

    def create_hotkey(self) -> None:
        """
        Creates a global hotkey for toggling the visibility of the application window.
        """

        self.hotkey_return_value = add_hotkey(self.settings_store["visibility_hotkey"]["value"],
                                              self.toggle_app_visibility)

    def set_default_quotes(self) -> None:
        """
        Sets default quotes if the quotes database is empty or does not exist.
        """

        if not self.quotes_store.exists("quotes") or len(self.quotes_store["quotes"]["quotes"]) == 0:
            self.quotes_store["quotes"] = {"quotes": [
                {"content": "You can tell whether a man is clever by his answers. You can tell whether a man "
                            "is wise by his questions.", "author": "Naguib Mahfouz"},
                {'content': 'The first duty of a human being is to assume the right functional relationship to'
                            ' society - more briefly, to find your real job, and do it.',
                 'author': 'Charlotte Perkins Gilman'},
                {'content': 'Strength does not come from physical capacity. It comes from an indomitable will.',
                 'author': 'Mahatma Gandhi'},
                {'content': "Never reach out your hand unless you're willing to extend an arm.",
                 'author': 'Pope Paul VI'},
                {'content': "Don't settle for a relationship that won't let you be yourself.",
                 'author': 'Oprah Winfrey'}
            ]}

    def set_default_settings(self) -> None:
        """
        Sets default values for application settings if they do not exist.
        """

        default_settings = {
            "user_name": "",
            "time_format": "AM/PM",
            "eyes_freq": "20 min",
            "water_freq": "45 min",
            "exercise_freq": "1 hr",
            "visibility_hotkey": "Ctrl + Shift + W",
            "water_intake": "200"
        }

        for key in default_settings:
            if not self.settings_store.exists(key):
                self.settings_store[key] = {"value": default_settings[key]}

    def on_start(self) -> None:
        TrayIconApp("Wellbeing", "assets/images/heart.ico",
                    ({"name": "Show", "action": self.show_app}, {"name": "Quit", "action": self.close_app}),
                    self.show_app).run_detached(True)
        self.create_hotkey()

    def build(self) -> ScreenManager:
        self.screen_manager.add_widget(HomeScreen())
        self.screen_manager.add_widget(ReminderScreen())
        self.screen_manager.add_widget(SettingsScreen())
        return self.screen_manager


if __name__ == "__main__":
    WellbeingApp().run()
