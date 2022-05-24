import paho.mqtt.client as mqtt
import json
import os.path

default_json = {
    "name": "default",
    "host": "public.mqtthq.com",
    "mqtt_client_name": "DEFAULT",
    "topic": "testml/",
    "keepalive": 60,
    "big_packet": False,
    "default_phase_duration": 999,
    "custom_phase_duration": {"example_tensor": 500},
}


def load_json():
    """
    Loads the values from the JSON config file. todo make file position dynamic?
    """
    if os.path.exists("mqtt_config.json"):
        f = open("mqtt_config.json", "r")
    else:
        f = open("mqtt_config.json", "w+")
        json.dump(default_json, f, indent=4)
    return json.load(f)


class AIModule:
    name: str
    topic: str
    default_phase: int
    big_packet: bool
    queues = dict()
    averages = dict()
    tensor_keys = []
    cache = dict()

    def __init__(self, tensor_list):
        self.tensor_keys = tensor_list
        json_values = load_json()
        self.load_config(json_values)
        self.queues = self.setup_queues(json_values)
        self.averages = self.setup_averages()
        self.cache = self.setup_occurrences()
        self.client = start_mqtt(json_values)

    def setup_occurrences(self):
        """
        Setups the dictionary needed for memoization.
        \nEx. {0} = 12, {1} = 2, {2} = 6
        \nThe most recurrent value is 0, being displayed 12 times out of a queue of 20(12 + 2 + 6).
        """

        return {key: {0: self.default_phase} for key in self.tensor_keys}

    def setup_averages(self):
        """
        Setups the dictionary that stores the number of instances of a tensor, this is the value that the server sees.
        \nEx. Shoes = 4, Hats = 2, Jackets = 6.
        """

        return {t: 0 for t in self.tensor_keys}

    def setup_queues(self, json_values):
        """
        Setups the queues of all the possible tensors. If the phase number for a tensor is 10, there will be 10 [0]'s in its queue when the module starts
        \nEx. Shoes = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        \nIf a Shoe is detected on scene, then a 1 will appear at the start of the queue. Since the most recurrent occurrence is still 0, no update is sent, until there are at least 5/10 1's in the queue.
        """
        return {t: [0] * (self.default_phase if t not in json_values["custom_phase_duration"] else json_values["custom_phase_duration"][t]) for t in self.tensor_keys}

    def load_config(self, config_dict: dict):
        """
        Loads name, topic, default_phase and pig_packet in the fields of the objects, for reusing them at runtime.
        """

        self.name = config_dict["name"]
        self.topic = config_dict["topic"]
        self.default_phase = config_dict["default_phase_duration"]
        self.big_packet = config_dict["big_packet"]

    def update(self, tensors):

        notify = False
        for t, array in self.queues.items():
            occurrences = self.cache[t]
            new = int(tensors.get(t, 0))

            # QUEUE MANAGING
            old: int = array.pop(0)  # last element gets popped out of queue
            array += [new]  # puts new number in queue

            # CACHED OCCURRENCES MANAGING
            # we use cache to get the biggest occurrence with a max over a dict of {"tensor" : number of obj}
            occurrences[new] = occurrences.get(new, 0) + 1  # increment tensor number in cache
            occurrences[old] -= 1  # decrements tensor number in cache

            new_avg = max(occurrences.items(), key=lambda a: a[1])[0]
            # a = self.averages[t]  # DEBUG
            if self.averages[t] != new_avg:
                self.averages[t] = new_avg
                notify = True
                if not self.big_packet:
                    self.client.publish(self.topic, f"{self.name}_{t}={new_avg}")
        if notify and self.big_packet:
            self.client.publish(self.topic, str(self.averages))


def start_mqtt(config):
    client = mqtt.Client(config["mqtt_client_name"])
    client.connect(config["host"], keepalive=config["keepalive"])
    client.subscribe(config["topic"])
    client.loop_start()
    return client
