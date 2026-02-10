# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from collections.abc import Collection

# https://support.apple.com/en-us/101183
# Maximum additional location location_id_2, location_id_3, up to location_id_999.
ADDITIONAL_LOCATION_LIMIT = 998
ADDITIONAL_INSTRUCTOR_LIMIT = 12


def validate_additional_location_limit(additional_location_ids: Collection[str]) -> None:
    if len(additional_location_ids) > ADDITIONAL_LOCATION_LIMIT:
        msg = f"No more than {ADDITIONAL_LOCATION_LIMIT} additional locations are allowed."
        raise ValueError(msg)


def validate_additional_instructor_limit(additional_instructor_ids: Collection[str]) -> None:
    if len(additional_instructor_ids) > ADDITIONAL_INSTRUCTOR_LIMIT:
        msg = f"No more than {ADDITIONAL_INSTRUCTOR_LIMIT} additional instructors are allowed."
        raise ValueError(msg)
