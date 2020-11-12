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

"""Main python script
"""

import os

import torch.multiprocessing as mp
import torch.distributed.rpc as rpc
from torch.optim import RMSprop, Adam
import torch.autograd.profiler as profiler

from pytorch_seed_rl.agents import Learner
from pytorch_seed_rl.environments import EnvSpawner
from pytorch_seed_rl.nets import AtariNet
#from pytorch_seed_rl.model import Model

ENV_ID = 'BreakoutNoFrameskip-v4'
ENV_SHORT = 'Breakout'
NUM_ENVS = 1

LEARNER_NAME = "learner{}"
ACTOR_NAME = "actor{}"
TOTAL_EPISODE_STEP = 1000

# torchbeast settings
# SETTINGS_NAME = '_torchbeast'
# BATCHSIZE_INF = 64
# BATCHSIZE_TRAIN = 4
# ROLLOUT = 80
# LEARNING_RATE = 0.0004

# mf planning settings
# SETTINGS_NAME = '_mfp'
# BATCHSIZE_INF = 16
# BATCHSIZE_TRAIN = 16
# ROLLOUT = 64
# LEARNING_RATE = 0.0005

# IMPALA settings
# SETTINGS_NAME = '_IMPALA'
# BATCHSIZE_INF = 16
# BATCHSIZE_TRAIN = 32
# ROLLOUT = 20
# LEARNING_RATE = 0.0006

# own settings
# SETTINGS_NAME = '_own'
# BATCHSIZE_INF = 8
# BATCHSIZE_TRAIN = 4
# ROLLOUT = 64
# LEARNING_RATE = 0.0006

# own settings
SETTINGS_NAME = '_test'
BATCHSIZE_INF = 2
BATCHSIZE_TRAIN = 4
ROLLOUT = 64
LEARNING_RATE = 0.0006

NUM_LEARNERS = 1
NUM_ACTORS = 2
CSV_FILE = './csv/'

USE_LSTM = False

EXPERIMENT_NAME = ENV_SHORT + SETTINGS_NAME


def run_threads(rank, world_size, env_spawner, model, optimizer):
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '29500'
    options = rpc.TensorPipeRpcBackendOptions(num_worker_threads=world_size)

    if rank < NUM_LEARNERS:
        # rank < NUM_LEARNERS are learners
        rpc.init_rpc(LEARNER_NAME.format(rank),
                     backend=rpc.BackendType.PROCESS_GROUP,
                     rank=rank,
                     world_size=world_size,
                     #   rpc_backend_options=options
                     )

        learner_rref = rpc.remote(LEARNER_NAME.format(rank),
                                  Learner,
                                  args=(rank,
                                        NUM_LEARNERS,
                                        NUM_ACTORS,
                                        env_spawner,
                                        model,
                                        optimizer),
                                  kwargs={'max_steps': TOTAL_EPISODE_STEP,
                                          'exp_name': EXPERIMENT_NAME,
                                          'inference_batchsize': BATCHSIZE_INF,
                                          'training_batchsize': BATCHSIZE_TRAIN,
                                          'rollout_length': ROLLOUT,
                                          })

        training_rref = learner_rref.remote().loop()
        training_rref.to_here(timeout=0)
    else:
        rpc.init_rpc(ACTOR_NAME.format(rank),
                     backend=rpc.BackendType.PROCESS_GROUP,
                     rank=rank,
                     world_size=world_size,
                     #  rpc_backend_options=options
                     )

    # block until all rpcs finish
    rpc.shutdown()


def main():
    # create and wrap environment
    env_spawner = EnvSpawner(ENV_ID, NUM_ENVS)

    # model
    model = AtariNet(
        env_spawner.env_info['observation_space'].shape,
        env_spawner.env_info['action_space'].n,
        USE_LSTM
    )

    optimizer = RMSprop(
        model.parameters(),
        lr=LEARNING_RATE,
        momentum=0,
        eps=0.01,
        alpha=0.99
    )

    # optimizer = Adam(
    #     model.parameters(),
    #     lr=LEARNING_RATE
    # )

    world_size = NUM_LEARNERS + NUM_ACTORS

    mp.set_start_method('spawn')
    mp.spawn(
        run_threads,
        args=(world_size, env_spawner, model, optimizer),
        nprocs=world_size,
        join=True
    )


if __name__ == '__main__':
    main()
