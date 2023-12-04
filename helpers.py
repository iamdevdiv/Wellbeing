# <<< IMPORTS AND CONFIGURATION >>>

from os import getcwd
from os.path import join
from winotify import Notification


# <<< HELPER FUNCTIONS >>>

def format_time(minutes: int) -> str:
    """
    Formats a given duration in minutes into a human-readable string.

    :param minutes: The duration in minutes to be formatted.
    :return: A formatted string representing the duration in hours and/or minutes.
    """

    if minutes == 0:
        return "0 minutes"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    formatted_time = ""

    if hours:
        formatted_time += f"{hours} hours" if hours > 1 else "1 hour"
    if hours and remaining_minutes:
        formatted_time += " and "
    if remaining_minutes:
        formatted_time += f"{remaining_minutes} minutes" if remaining_minutes > 1 else "1 minute"

    return formatted_time


def notify(title: str, message: str, icon: str) -> None:
    """
    Displays a notification with the specified title, message, and icon.

    :param title: The title of the notification.
    :param message: The message content of the notification.
    :param icon: The name of the icon file (without extension) located in "assets/images/".
    """

    toast = Notification(app_id="Wellbeing",
                         title=title,
                         msg=message,
                         icon=join(getcwd(), f"assets/images/{icon}.png"))
    toast.show()
