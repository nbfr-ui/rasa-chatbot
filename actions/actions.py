from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

def find_entity_value(tracker: Tracker, name_of_entity: str, type_of_entity: str):
    raw_entity = list(filter(lambda e: e['entity'] == name_of_entity,
                                     tracker.latest_message['entities']))[0]
    matching_number_entity = list(filter(lambda e: e['entity'] == type_of_entity and
                                              e['start'] == raw_entity['start'] and
                                              e['end'] == raw_entity['end'],
                                    tracker.latest_message["entities"]))[0]
    return matching_number_entity['value']

class ActionBla(Action):

    def name(self) -> Text:
        return "action_bla"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        number_of_guests = int(find_entity_value(tracker, 'number_of_guests', 'number'))
        return [SlotSet("number_of_guests", number_of_guests)]

