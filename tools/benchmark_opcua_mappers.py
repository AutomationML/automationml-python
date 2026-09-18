"""Small reproducible comparison of the Python and XSLT forward mappers."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from statistics import median
from time import perf_counter

from lxml import etree

from automationml import CAEXFile
from automationml.opcua import UA_NODESET_NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))

from opcua_evaluation import patched_xslt_nodeset_xml


DEFAULT_FIXTURES = (
    "0_EmptyFile_V2.1.aml",
    "2_IE.aml",
    "3_IE_Attribute.aml",
    "4_IH.aml",
    "5_SUC.aml",
)
NS = {"ua": UA_NODESET_NS}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    fixture_root = Path(__file__).parents[1] / "tests" / "fixtures" / "opcua_reverse"

    print("fixture\tmapper\tmedian_ms\tbytes\tnodes\treferences\troundtrip")
    for fixture_name in DEFAULT_FIXTURES:
        document = CAEXFile.from_aml_xml((fixture_root / fixture_name).read_bytes())
        expected = document.to_aml_dict()
        for mapper in ("python", "xslt"):
            timings: list[float] = []
            output = ""
            aml_xml = document.to_aml_xml(
                pretty=False,
                include_default_change_mode=True,
            ).encode()
            for _ in range(args.repeats):
                started = perf_counter()
                if mapper == "xslt":
                    output = patched_xslt_nodeset_xml(
                        aml_xml,
                        publication_date="2026-08-17",
                        pretty=False,
                    )
                else:
                    output = document.to_opcua_nodeset_xml(
                        include_roundtrip=False,
                        pretty=False,
                        publication_date="2026-08-17",
                    )
                timings.append((perf_counter() - started) * 1000)
            root = etree.fromstring(output.encode())
            recovered = CAEXFile.from_opcua_nodeset_xml(output).to_aml_dict()
            print(
                "\t".join(
                    (
                        fixture_name,
                        mapper,
                        f"{median(timings):.3f}",
                        str(len(output.encode())),
                        str(int(root.xpath("count(./ua:*[@NodeId])", namespaces=NS))),
                        str(int(root.xpath("count(.//ua:Reference)", namespaces=NS))),
                        "yes" if recovered == expected else "no",
                    )
                )
            )


if __name__ == "__main__":
    main()
