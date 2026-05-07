"""
Snowflake connection wrapper that reads Snow CLI connection profiles.

Snow CLI stores profiles in TOML at ~/.snowflake/config.toml:

  [connections]
  [connections.myconn]
  account = "xy12345.us-east-1"
  user = "alice"
  password = "secret"
  warehouse = "COMPUTE_WH"
  database = "ANALYTICS"
  role = "SYSADMIN"

snowconn 3.14.x reads ~/.snowsql/config (INI), not TOML, so we parse
the Snow CLI TOML ourselves and call SnowConn.connect_credentials().
"""

import tomllib
from pathlib import Path

from snowconn import SnowConn

_DEFAULT_CONFIG = Path.home() / ".snowflake" / "config.toml"


def _load_profile(config_path: Path, connection_name: str | None) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Snow CLI config not found at {config_path}. "
            "Run 'snow connection add' or create the file manually."
        )
    with config_path.open("rb") as f:
        config = tomllib.load(f)

    connections = config.get("connections", {})

    if connection_name is None:
        # Default profile sits directly under [connections] as non-dict values
        profile = {k: v for k, v in connections.items() if not isinstance(v, dict)}
        if not profile:
            available = [k for k, v in connections.items() if isinstance(v, dict)]
            raise KeyError(
                f"No default connection profile found in {config_path}. "
                f"Available named profiles: {available}. "
                "Pass --connection <name> to select one."
            )
        return profile

    if connection_name not in connections or not isinstance(
        connections[connection_name], dict
    ):
        available = [k for k, v in connections.items() if isinstance(v, dict)]
        raise KeyError(
            f"Connection '{connection_name}' not found in {config_path}. "
            f"Available: {available}"
        )
    return connections[connection_name]


def get_connection(
    connection_name: str | None = None,
    database: str | None = None,
    schema: str | None = None,
    config_path: Path | None = None,
) -> SnowConn:
    """Return a connected SnowConn using the named Snow CLI profile.

    Args:
        connection_name: Profile name from [connections.<name>] in config.toml.
                         None uses the flat [connections] default profile.
        database: Override the database from the profile.
        schema: Override the schema from the profile.
        config_path: Override config file path (useful for testing).
    """
    path = config_path or _DEFAULT_CONFIG
    profile = _load_profile(path, connection_name)

    return SnowConn.connect_credentials(
        account=profile["account"],
        username=profile["user"],
        password=profile.get("password", ""),
        authenticator=profile.get("authenticator"),
        db=database or profile.get("database", "PUBLIC"),
        schema=schema or profile.get("schema", "PUBLIC"),
        role=profile.get("role"),
        warehouse=profile.get("warehouse"),
    )
