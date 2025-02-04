from gymnasium.envs.registration import register
from custom_envs.object_placement_v2 import ComponentPlacementEnvironment

register(
    id='ComponentPlacementEnvironment-v2',
    entry_point='custom_envs.object_placement_v2:ComponentPlacementEnvironment',
)