from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import requests
from dateutil import parser

class ActionBla(Action):

    def name(self) -> Text:
        return "action_bla"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [SlotSet("number_of_guests", None)]

def extract_value(
        tracker: Tracker, slot_name: str, entity_name: str, duckling_dimension: str,
) -> Any:
    entity = next(tracker.get_latest_entity_values(entity_name), None)
    parsed_value = query_duckling(entity if entity is not None else tracker.latest_message['text'], duckling_dimension)
    if entity is not None and parsed_value is not None:
        return parsed_value
    elif tracker.slots['requested_slot'] == slot_name and parsed_value is not None:
        return parsed_value
    return None

def query_duckling(
        text: str,
        dimension: str
) -> Any:
    response = requests.post('http://0.0.0.0:8000/parse', data={"text": text, "dims": [dimension]}).json()
    if len(response) > 0:
        return response[0]['value']['value']
    return None

def set_slot_or_show_error(
        dispatcher: CollectingDispatcher, tracker: Tracker, value: Any, slot_name: str, error_msg: str = "Sorry I didn't understand"
) -> Dict[Text, Any]:
    if value is not None:
        return {slot_name: value}
    elif tracker.slots['requested_slot'] == slot_name:
        dispatcher.utter_message(error_msg)
    return {}

class ValidateBookingForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_booking_form"

    async def extract_from_date(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        value = extract_value(tracker, 'from_date','from_date', 'time')
        return set_slot_or_show_error(dispatcher, tracker, value, 'from_date')

    async def extract_duration_of_stay(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        value = extract_value(tracker, 'duration_of_stay', 'duration_of_stay', 'number')
        return set_slot_or_show_error(dispatcher, tracker, value, 'duration_of_stay')

    async def extract_number_of_guests(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        value = extract_value(tracker, 'number_of_guests', 'number_of_guests', 'number')
        return set_slot_or_show_error(dispatcher, tracker, value, 'number_of_guests')


class ActionBookingSummary(Action):

    def name(self) -> Text:
        return "action_booking_summary"

    def calculate_price(self, duration_in_days: int):
        return duration_in_days * 100

    def format_date(self, value: str):
        return parser.isoparse(value).date()

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        text = f"""Here is your booking summary: \n
        \n
        Name of the main guest: {tracker.slots['name']}\n
        Number of guests: {tracker.slots['number_of_guests']}\n
        Date of arrival: {self.format_date(tracker.slots['from_date'])}\n
        Duration of stay: {tracker.slots['duration_of_stay']} nights\n
        With breakfast: {'yes' if tracker.slots['number_of_guests'] else 'no'}\n
        \n
        Total costs: ${self.calculate_price(int(tracker.slots['duration_of_stay']))}\n
        \n
        Would you like to confirm your booking? (y/n)"""
        dispatcher.utter_message(text=text)
        return []
