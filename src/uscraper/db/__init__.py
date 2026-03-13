"""
Database layer: connection, schema, app config, browsers/drivers, profiles, runs.
"""
from uscraper.db.connection import ensure_db, get_connection, init_schema
from uscraper.db.app_config import get_config, set_config, get_config_default
from uscraper.db.browsers import (
    seed_browsers_if_empty,
    list_browsers,
    get_browser_by_id,
    get_browser_by_internal_name,
    update_driver,
    set_driver_last_used,
)
from uscraper.db.profiles import (
    create_profile,
    get_profile,
    list_profiles,
    update_profile,
    delete_profile,
    add_element,
    get_elements_for_profile,
    update_element,
    delete_element,
    get_profile_with_elements,
)
from uscraper.db.runs import (
    start_run,
    complete_run,
    fail_run,
    get_run,
    list_runs_for_profile,
)

__all__ = [
    "ensure_db",
    "get_connection",
    "init_schema",
    "get_config",
    "set_config",
    "get_config_default",
    "seed_browsers_if_empty",
    "list_browsers",
    "get_browser_by_id",
    "get_browser_by_internal_name",
    "update_driver",
    "set_driver_last_used",
    "create_profile",
    "get_profile",
    "list_profiles",
    "update_profile",
    "delete_profile",
    "add_element",
    "get_elements_for_profile",
    "update_element",
    "delete_element",
    "get_profile_with_elements",
    "start_run",
    "complete_run",
    "fail_run",
    "get_run",
    "list_runs_for_profile",
]
