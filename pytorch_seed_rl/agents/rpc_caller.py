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

"""RPC object that handles communication with an assigned RPC callee.
"""
from torch.distributed import rpc

from abc import abstractmethod


class RpcCaller():
    """RPC object that handles communication with an assigned RPC callee.
    """

    def __init__(self, rank, callee_rref):
        self.callee_rref = callee_rref

        self.id = rpc.get_worker_info().id
        self.name = rpc.get_worker_info().name
        self.rank = rank

        self.shutdown = False

    def loop(self):
        """Loop acting method.
        """
        self.callee_rref.rpc_sync().check_in(self.rank)

        self._loop()

        self.callee_rref.rpc_sync().check_out(self.rank)

        return True

    @abstractmethod
    def _loop(self):
        raise NotImplementedError

    def batched_rpc(self, *args, **kwargs):
        """Wrap for batched async RPC ran on remote callee.
        """
        return self.callee_rref.rpc_async().batched_process(*args, **kwargs)
