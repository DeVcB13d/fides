"""Module for interaction with User endpoints/commands."""
import json
from typing import Dict, List, Tuple

import requests

from fides.api.ops.api.v1.scope_registry import SCOPE_REGISTRY as SCOPES
from fides.cli.utils import handle_cli_response
from fides.core.config import get_config
from fides.core.utils import (
    Credentials,
    echo_green,
    echo_red,
    get_auth_header,
    get_credentials_path,
    read_credentials_file,
    write_credentials_file,
)
from fides.lib.cryptography.cryptographic_util import str_to_b64_str

config = get_config()
CREATE_USER_PATH = "/api/v1/user"
LOGIN_PATH = "/api/v1/login"
USER_PERMISSIONS_PATH = "/api/v1/user/{}/permission"


def get_access_token(username: str, password: str, server_url: str) -> Tuple[str, str]:
    """
    Get a user access token from the webserver.
    """
    payload = {
        "username": username,
        "password": str_to_b64_str(password),
    }

    response = requests.post(server_url + LOGIN_PATH, json=payload)
    handle_cli_response(response, verbose=False)
    user_id: str = response.json()["user_data"]["id"]
    access_token: str = response.json()["token_data"]["access_token"]
    return (user_id, access_token)


def create_user(
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    auth_header: Dict[str, str],
    server_url: str,
) -> requests.Response:
    """Create a user."""
    request_data = {
        "username": username,
        "password": str_to_b64_str(password),
        "first_name": first_name,
        "last_name": last_name,
    }
    response = requests.post(
        server_url + CREATE_USER_PATH,
        headers=auth_header,
        data=json.dumps(request_data),
    )
    handle_cli_response(response, verbose=False)
    return response


def get_user_permissions(
    user_id: str, auth_header: Dict[str, str], server_url: str
) -> List[str]:
    """
    List all of the user permissions for the provided user.
    """
    get_permissions_path = USER_PERMISSIONS_PATH.format(user_id)
    response = requests.get(
        server_url + get_permissions_path,
        headers=auth_header,
    )

    handle_cli_response(response, verbose=False)
    return response.json()["scopes"]


def update_user_permissions(
    user_id: str, scopes: List[str], auth_header: Dict[str, str], server_url: str
) -> requests.Response:
    """
    Update user permissions for a given user.
    """
    request_data = {"scopes": scopes, "id": user_id}
    set_permissions_path = USER_PERMISSIONS_PATH.format(user_id)
    response = requests.put(
        server_url + set_permissions_path,
        headers=auth_header,
        json=request_data,
    )
    handle_cli_response(response=response, verbose=False)
    return response


def create_command(
    username: str, password: str, first_name: str, last_name: str, server_url: str
) -> None:
    """
    Given new user information, create a new user via the API using
    the local credentials file.
    """

    auth_header = get_auth_header()
    user_response = create_user(
        username=username,
        password=password,
        first_name=first_name,
        last_name=last_name,
        auth_header=auth_header,
        server_url=server_url,
    )
    user_id = user_response.json()["id"]
    update_user_permissions(
        user_id=user_id, scopes=SCOPES, auth_header=auth_header, server_url=server_url
    )
    echo_green(f"User: '{username}' created and assigned permissions.")


def login_command(username: str, password: str, server_url: str) -> str:
    """
    Given a username and password, request an access_token from the API and
    store all user information in a local credentials file.
    """
    user_id, access_token = get_access_token(
        username=username, password=password, server_url=server_url
    )
    echo_green(f"Logged in as user: {username}")
    credentials = Credentials(
        username=username, password=password, user_id=user_id, access_token=access_token
    )
    credentials_path = get_credentials_path()
    write_credentials_file(credentials, credentials_path)
    echo_green(f"Credentials file written to: {credentials_path}")
    return credentials_path


def get_permissions_command(server_url: str) -> None:
    """
    Get user permissions from the API.
    """
    credentials_path = get_credentials_path()
    try:
        credentials = read_credentials_file(credentials_path)
    except FileNotFoundError:
        echo_red(f"No credentials file found at path: {credentials_path}")
        raise SystemExit(1)

    user_id = credentials.user_id
    auth_header = get_auth_header()
    permissions: List[str] = get_user_permissions(user_id, auth_header, server_url)

    print("Permissions:")
    for permission in permissions:
        print(f"\t{permission}")
