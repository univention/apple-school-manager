#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test ASM API constraints helpers
## tags: [apptest]  # noqa: ERA001
## exposure: safe  # noqa: ERA001
## packages:
##   - python3-univention-apple-school-manager-connector
## bugs: [58988]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from collections.abc import Callable, Collection

import pytest
from univention.asm.api_constraints import (
    ADDITIONAL_INSTRUCTOR_LIMIT,
    ADDITIONAL_LOCATION_LIMIT,
    validate_additional_instructor_limit,
    validate_additional_location_limit,
)


@pytest.mark.parametrize(
    ("validator", "limit"),
    [
        (validate_additional_location_limit, ADDITIONAL_LOCATION_LIMIT),
        (validate_additional_instructor_limit, ADDITIONAL_INSTRUCTOR_LIMIT),
    ],
)
def test_validator_enforces_limit(validator: Callable[[Collection[str]], None], limit: int) -> None:
    validator([])
    validator(["item_id"] * limit)
    with pytest.raises(ValueError):  # noqa: PT011
        validator(["item_id"] * (limit + 1))
