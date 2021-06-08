"""
This module handles everything related to parsing models,
either from local files or the server.
"""
from typing import Any, Dict

from .utils import echo_red, MODEL_DICT


def parse_manifest(object_type: str, _object: Dict, from_server: bool = False) -> Any:
    """
    Parse an individual object into its related model.
    Remove extra (unsupported) fields from the object prior to parsing if needed.
    """
    object_source = "server" if from_server else "manifest file"

    try:
        parsed_manifest = MODEL_DICT[object_type].parse_obj(_object)
    except Exception as err:
        echo_red(
            "Failed to parse {} from {} with fidesKey: {}".format(
                object_type, object_source, _object["fidesKey"]
            )
        )
        raise SystemExit(err)
    return parsed_manifest
