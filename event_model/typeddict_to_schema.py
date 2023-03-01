from pathlib import Path
import re
import json
from pydantic import create_model, BaseModel, Extra, BaseConfig
from typing import Type, Optional, Dict, Any
from event_model import SCHEMA_PATH
from event_model.documents._type_wrapper import extra_schema
from event_model.documents import (
    DatumPage,
    Datum,
    EventDescriptor,
    EventPage,
    Event,
    Resource,
    RunStart,
    RunStop,
    StreamDatum,
    StreamResource,
)

SCHEMA_OUT_DIR = Path("event_model") / SCHEMA_PATH


# Used to add user written schema to autogenerated schema.
def merge_dicts(dict1: dict, dict2: dict) -> dict:
    """
    Takes two dictionaries with subdirectories and returns a new dictionary of the two merged:
    dict1 = {
        "x1": {
            "y1": 0,  "y3": {"z1" : [1, 2], "z2": 1}
        },
        "x2" : 0,
        "x3": 1
    }
    and
    dict2 = {
        "x1": {
            "y2" : 0,  "y3": {"z1": [3, 4], "z3": 5}
        },
        "x3" : 0
    }
    returns
    {
        "x1": {
            "y1": 0, "y2": 0,  "y3": {"z1": [1, 2, 3, 4], "z2": 1, "z3": 5}
        },
        "x2": 0
        "x3": 1
    }
    """

    return_dict = dict2.copy()

    for key in dict1:
        if key not in dict2:
            return_dict[key] = dict1[key]

        elif not isinstance(dict1[key], type(dict2[key])):
            return_dict[key] = dict1[key]

        elif isinstance(dict1[key], dict):
            return_dict[key] = merge_dicts(dict1[key], dict2[key])

        elif isinstance(dict1[key], list):
            return_dict[key] = dict1[key] + dict2[key]

    return return_dict


# Config for generated BaseModel
class Config(BaseConfig):
    extra = Extra.forbid

    # Alias in snake case
    def alias_generator(string_to_be_aliased):
        return re.sub(r"(?<!^)(?=[A-Z])", "_", string_to_be_aliased).lower()


# From https://github.com/pydantic/pydantic/issues/760#issuecomment-589708485
def parse_typeddict_to_schema(
    typed_dict: Any,
    out_dir: Optional[Path] = None,
) -> Type[BaseModel]:
    annotations: Dict[str, Any] = {}

    for name, field in typed_dict.__annotations__.items():
        if isinstance(field, dict):
            annotations[name] = (
                parse_typeddict_to_schema(field),
                ...,
            )
        else:
            default_value = getattr(typed_dict, name, ...)
            annotations[name] = (field, default_value)

    model = create_model(typed_dict.__name__, __config__=Config, **annotations)

    # Docstring is used as the description field.
    model.__doc__ = typed_dict.__doc__

    # title goes to snake_case
    model.__name__ = Config.alias_generator(typed_dict.__name__).lower()
    model_schema = model.schema(by_alias=True)

    model_schema["description"] = typed_dict.__doc__

    # Add the manually defined extra stuff
    if typed_dict in extra_schema:
        model_schema = merge_dicts(extra_schema[typed_dict], model_schema)

    if out_dir:
        with open(out_dir / f'{model_schema["title"]}.json', "w+") as f:
            json.dump(model_schema, f, indent=3)

    return model_schema


def generate_all_schema(schema_out_dir: Path = SCHEMA_OUT_DIR) -> None:
    parse_typeddict_to_schema(DatumPage, out_dir=schema_out_dir)
    parse_typeddict_to_schema(Datum, out_dir=schema_out_dir)
    parse_typeddict_to_schema(EventDescriptor, out_dir=schema_out_dir)
    parse_typeddict_to_schema(EventPage, out_dir=schema_out_dir)
    parse_typeddict_to_schema(Event, out_dir=schema_out_dir)
    parse_typeddict_to_schema(Resource, out_dir=schema_out_dir)
    parse_typeddict_to_schema(RunStart, out_dir=schema_out_dir)
    parse_typeddict_to_schema(RunStop, out_dir=schema_out_dir)
    parse_typeddict_to_schema(StreamDatum, out_dir=schema_out_dir)
    parse_typeddict_to_schema(StreamResource, out_dir=schema_out_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--schema_out_directory", default=SCHEMA_OUT_DIR, nargs="?")
    args = parser.parse_args()
    generate_all_schema(schema_out_dir=args.schema_out_directory)
