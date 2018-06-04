import nbtlib

from ...schema import schema

effect = schema('common.effect', {
    'Ambient': nbtlib.Byte,
    'Amplifier': nbtlib.Byte,
    'Duration': nbtlib.Int,
    'Id': nbtlib.Byte,
    'ShowParticles': nbtlib.Byte,
})
