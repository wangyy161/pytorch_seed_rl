# Copyright 2020 Michael Janschek
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=not-callable, missing-module-docstring, missing-class-docstring, missing-function-docstring, too-many-arguments, arguments-differ

"""The store class can be configured for various data structures.
"""

#from .structure import Trajectory
import copy
import torch
from collections import deque


class TrajectoryStore():
    """The store class can:
        #. save and load info for a given unique key (hashmap?)
        #. store a predefined data structure (not that flexible :-/)
    """

    def __init__(self, num_keys, zero_obs, device, max_trajectory_length=128):

        self.device = device
        self.zero_obs = zero_obs
        self.max_trajectory_length = max_trajectory_length
        self.trajectory_counter = 0
        self.drop_off_queue = deque(maxlen=num_keys)
        self.internal_store = [self._new_trajectory() for _ in range(num_keys)]

    def _new_trajectory(self):
        trajectory = {
            "global_trajectory_number": torch.tensor(self.trajectory_counter),
            "complete": torch.tensor(False),
            "current_length": torch.tensor(0),
            "states": self._new_states(),
            # "metrics": []
        }

        self.trajectory_counter += 1

        return trajectory

    def _new_states(self):
        states = {}
        for key, value in self.zero_obs.items():
            states[key] = value.repeat(
                (self.max_trajectory_length,) + (1,)*(len(value.size())-1))
        return states

    def _reset_trajectory(self, i):
        self.trajectory_counter += 1
        trajectory = self.internal_store[i]
        trajectory['global_trajectory_number'].fill_(self.trajectory_counter)
        trajectory['complete'].fill_(False)
        trajectory['current_length'].fill_(0)
        #trajectory['metrics'] = []

        self._reset_states(trajectory['states'])

    @staticmethod
    def _reset_states(states):
        for value in states.values():
            value.fill_(0)

    def add_to_entry(self, i, state, metrics=None):
        trajectory = self.internal_store[i]
        current_length = trajectory['current_length'].item()
        states = trajectory['states']

        for key, value in state.items():
            states[key][current_length].copy_(value[0])

        trajectory['current_length'] += 1
        if state['done'] and state['episode_step'] > 0:
            trajectory["complete"].fill_(True)

        if trajectory["complete"] or (trajectory['current_length'] == self.max_trajectory_length):
            self._drop(trajectory)
            self._reset_trajectory(i)

        # trajectory["metrics"].append(metrics)

    def _drop(self, trajectory):
        self.drop_off_queue.append(copy.deepcopy(trajectory))
