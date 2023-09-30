from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
import requests
from dateutil import parser
from datetime import datetime


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
    response = requests.post('http://0.0.0.0:8000/parse', data={"text": text, "dims": f'["{dimension}"]' }).json()
    if len(response) > 0:
        if 'value' in response[0]['value']:
            return response[0]['value']['value']
        elif 'values' in response[0]['value']:
            return response[0]['value']['values'][0]
    return None


def show_error_if_slot_requested(
        dispatcher: CollectingDispatcher, tracker: Tracker, slot_name: str, error_msg: str = "Sorry I didn't understand"
) -> Dict[Text, Any]:
    if tracker.slots['requested_slot'] == slot_name:
        dispatcher.utter_message(error_msg)
    return {}


class ValidateBookingForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_booking_form"

    def _validate_number(self, num: str | int | None, min: int, max: int):
        if num is None:
            return False
        try:
            as_int = int(num)
            if as_int < min or as_int > max:
                raise ValueError
            return True
        except ValueError:
            return False

    async def extract_from_date(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        value = extract_value(tracker, 'from_date','from_date', 'time')
        if value is not None:
            try:
                parsed = parser.isoparse(value)
                if parsed < datetime.now(tz=parsed.tzinfo):
                    dispatcher.utter_message('The booking date must not lie in the past.')
                    return {}
                return { 'from_date': value }
            except ValueError:
                dispatcher.utter_message('Invalid booking date.')
        return {}

    async def extract_duration_of_stay(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        value = extract_value(tracker, 'duration_of_stay', 'duration_of_stay', 'number')
        if value is None and 'from_date' in tracker.slots and tracker.slots['from_date'] is not None:
            until_date = next(tracker.get_latest_entity_values('until_date'), None)
            if until_date is not None:
                until_iso_date = query_duckling(until_date, 'time')
                if until_iso_date is not None:
                    value = (parser.isoparse(until_iso_date) - parser.isoparse(tracker.slots['from_date'])).days
        if value is not None:
            if self._validate_number(value, 1, 30):
                return {"duration_of_stay": value}
            else:
                dispatcher.utter_message('Duration is invalid. The duration of your stay must be at least one night'
                                         ' and no longer than 30 nights')
        return {}

    async def extract_number_of_guests(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        value = extract_value(tracker, 'number_of_guests', 'number_of_guests', 'number')
        if value is not None:
            if self._validate_number(value, 1, 3):
                return {"number_of_guests": value}
            else:
                dispatcher.utter_message('The number of guests is invalid. The number of guests for a booking must '
                                         'be between 1 and 3. We don\'t offer rooms for more than 3 guests')
        return {}

    async def extract_email(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> Dict[Text, Any]:
        value = extract_value(tracker, 'email_address', 'email', 'email')
        if value is None:
            return show_error_if_slot_requested(dispatcher, tracker, 'number_of_guests')
        else:
            return { 'email_address': value }

class ActionBookingSummary(Action):

    def name(self) -> Text:
        return "action_booking_summary"

    def calculate_price(self, duration_in_days: int, breakfast: bool):
        return duration_in_days * (110 if breakfast else 100)

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
        With breakfast: {'yes' if tracker.slots['breakfast'] else 'no'}\n
        \n
        Total costs: ${self.calculate_price(int(tracker.slots['duration_of_stay']), tracker.slots['breakfast'])}\n
        \n
        Would you like to confirm your booking? (y/n)"""
        dispatcher.utter_message(text=text)
        return []
