import time
import paho.mqtt.client as mqtt

class AIModule:
    limit = 0
    tensors = {}
    averages = {}
    tensor_keys = []

    def __init__(self, age_length, tensor_list):
        self.limit = age_length
        self.tensor_keys = tensor_list
        self.tensors = {t: [0] * self.limit for t in tensor_list}
        self.averages = {t: 0 for t in tensor_list}
        self.client = start_mqtt()

    def update(self, tensors):
        notify = False
        for t, array in self.tensors.items():
            array += [int(tensors.get(t, 0))]
            del array[0]
            new_avg = self.get_max_occurrence(array)
            # a = self.averages[t]  # DEBUG
            if self.averages[t] != new_avg:
                notify = True
                self.averages[t] = new_avg
        if notify:
            self.client.publish("testml/", str(self.averages))
            print("\n" + str(self.averages) + "\n")

    def change_limit(self, limit):
        self.limit = limit

    def get_max_occurrence(self, iterator):  # could use some memoization
        occurrences = dict()
        for e in iterator:
            occurrences[e] = occurrences.get(e, 0) + 1
        return max(occurrences.items(), key=lambda a: a[1])[0]


def start_mqtt():
    client = mqtt.Client("LAPTOP-FRA")
    client.connect("public.mqtthq.com")
    client.subscribe("testml/")
    client.loop_start()
    return client
