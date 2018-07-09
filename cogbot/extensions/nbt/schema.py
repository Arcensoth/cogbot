import difflib
import logging

import nbtlib
from nbtq import errors

log = logging.getLogger(__name__)


def schema(name, dct, inherit=()):
    return type(name, (ValidationCompoundSchema,), {'__slots__': (), 'schema': dct, 'inherit': inherit})


class ValidationCompoundSchema(nbtlib.CompoundSchema):
    __slots__ = ()
    inherit = {}
    strict = True

    def _cast(self, key, value):
        schema_type = self.schema.get(key, None)

        if schema_type is None and self.inherit:
            # check parents
            for parent in self.inherit:
                if key in parent.schema:
                    schema_type = parent.schema.get(key)

        if schema_type is None:
            # check siblings
            siblings = self.schema.keys()
            match = difflib.get_close_matches(key, siblings, n=1, cutoff=0.6)
            if match:
                raise errors.SchemaValidationError(
                    f'Tag `{key}` does not exist on `{self.__class__.__name__}`, maybe you meant `{match[0]}`')
            raise errors.SchemaValidationError(
                f'Tag `{key}` does not exist on `{self.__class__.__name__}`')

        try:
            expected_value = schema_type(value)
        except errors.SchemaValidationError as e:
            raise e
        except:
            expected_value = None

        if value != expected_value:
            raise errors.SchemaValidationError(
                f'Tag `{key}` should be type `{schema_type.__name__}`')

        if issubclass(schema_type, nbtlib.Compound):
            pass

        elif issubclass(schema_type, nbtlib.List):
            for subvalue in value:
                if not (
                        isinstance(subvalue, (nbtlib.Compound, nbtlib.List))
                        or isinstance(subvalue, schema_type.subtype)
                ):
                    raise errors.SchemaValidationError(
                        f'Tag `{key}` should contain only `{schema_type.subtype.__name__}`, '
                        f'not `{subvalue.__class__.__name__}`')

        elif not isinstance(value, schema_type):
            raise errors.SchemaValidationError(
                f'Tag `{key}` should be type `{schema_type.__name__}` not `{value.__class__.__name__}`')

        return expected_value
