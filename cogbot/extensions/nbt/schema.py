import logging

import nbtlib

log = logging.getLogger(__name__)


class SchemaValidationError(TypeError):
    pass


def schema(name, dct):
    return type(name, (ValidationCompoundSchema,), {'__slots__': (), 'schema': dct})


class ValidationCompoundSchema(nbtlib.CompoundSchema):
    strict = True

    def _cast(self, key, value):
        schema_type = self.schema.get(key, None)

        if schema_type is None:
            raise SchemaValidationError(f'Tag `{key}` does not exist on `{self.__class__.__name__}`')

        try:
            expected_value = schema_type(value)
        except SchemaValidationError as e:
            raise e
        except:
            log.exception('')
            expected_value = None

        if value != expected_value:
            raise SchemaValidationError(
                f'Tag `{key}` should be type `{schema_type.__name__}`')

        if issubclass(schema_type, nbtlib.Compound):
            pass

        elif issubclass(schema_type, nbtlib.List):
            for item in value:
                if not isinstance(item, schema_type.subtype):
                    raise SchemaValidationError(
                        f'Tag `{key}` should contain only `{schema_type.subtype.__name__}`, '
                        f'not `{item.__class__.__name__}`')

        elif not isinstance(value, schema_type):
            raise SchemaValidationError(
                f'Tag `{key}` should be type `{schema_type.__name__}` not `{value.__class__.__name__}`')

        return expected_value
