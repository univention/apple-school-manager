# https://support.apple.com/en-us/101183
# Maximum additional location location_id_2, location_id_3, up to location_id_999.
ADDITIONAL_LOCATION_LIMIT = 998


def validate_additional_location_limit(additional_location_ids: list[str]) -> None:
    # TODO Remove assert for value checks (see bandit:B101)!
    assert len(additional_location_ids) <= ADDITIONAL_LOCATION_LIMIT, (
        f"No more than {ADDITIONAL_LOCATION_LIMIT} additional locations are allowed."
    )
