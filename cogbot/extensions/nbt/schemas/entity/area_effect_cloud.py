import nbtlib

from ...schema import schema
from ...schemas import common, entity

area_effect_cloud = schema('entity.area_effect_cloud', {
    'Age': nbtlib.Int,
    'Color': nbtlib.Int,
    'Duration': nbtlib.Int,
    'DurationOnUse': nbtlib.Float,
    'Effects': nbtlib.List[common.effect],
    'OwnerUUIDLeast': nbtlib.Long,
    'OwnerUUIDMost': nbtlib.Long,
    'Particle': nbtlib.String,
    'ParticleParam1': nbtlib.Int,
    'ParticleParam2': nbtlib.Int,
    'Potion': nbtlib.String,
    'Radius': nbtlib.Float,
    'RadiusOnUse': nbtlib.Float,
    'RadiusPerTick': nbtlib.Float,
    'ReapplicationDelay': nbtlib.Int,
    'WaitTime': nbtlib.Int
}, inherit=[entity.entity])
