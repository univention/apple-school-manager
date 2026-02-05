#!/usr/share/ucs-test/runner python3
## desc: test ASM API constraints helpers
## tags: [apptest]  # noqa: ERA001
## exposure: safe  # noqa: ERA001
## packages:
##   - python3-univention-apple-school-manager-connector
## bugs: [58988]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import unittest
from collections.abc import Callable, Collection

from univention.asm.api_constraints import (
    ADDITIONAL_LOCATION_LIMIT,
    validate_additional_location_limit,
)


class TestApiConstraints(unittest.TestCase):
    def _assert_validator_enforces_limit(
        self,
        validator: Callable[[Collection[str]], None],
        limit: int,
        dummy_item: str = "item_id",
    ) -> None:
        # test validator for empty list
        validator([])
        # test validator for list with exactly the limit number of items
        validator([dummy_item] * limit)
        # test validator raises ValueError for list with more than the limit number of items
        with self.assertRaises(ValueError):  # noqa: PT027
            validator([dummy_item] * (limit + 1))

    def test_validate_additional_location_limit_enforces_limit(self) -> None:
        self._assert_validator_enforces_limit(
            validator=validate_additional_location_limit,
            limit=ADDITIONAL_LOCATION_LIMIT,
        )


if __name__ == "__main__":
    unittest.main()
