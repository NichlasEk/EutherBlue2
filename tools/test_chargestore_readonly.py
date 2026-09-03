#!/usr/bin/env python3

import unittest

from chargestore_readonly import SAFE_QUERIES, crc8, decode, encode


class ChargestoreReadOnlyTest(unittest.TestCase):
    def test_known_read_queries_roundtrip(self) -> None:
        for payload in SAFE_QUERIES.values():
            self.assertEqual(decode(encode(payload)), payload)

    def test_sdk_version_query_wire_image(self) -> None:
        self.assertEqual(encode(SAFE_QUERIES["sdk-version"]).hex(), "55aa02210203")

    def test_crc_matches_sdk_algorithm(self) -> None:
        self.assertEqual(crc8(bytes.fromhex("55aa022102")), 0x03)

    def test_rejects_bad_crc(self) -> None:
        with self.assertRaisesRegex(ValueError, "CRC mismatch"):
            decode(bytes.fromhex("55aa02210200"))

    def test_only_read_queries_are_exposed(self) -> None:
        self.assertEqual(set(SAFE_QUERIES), {"bluetooth-name", "sdk-version", "battery"})


if __name__ == "__main__":
    unittest.main()
