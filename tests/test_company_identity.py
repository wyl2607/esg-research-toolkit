from report_parser.company_identity import canonical_company_name, company_names_match


def test_known_german_demo_aliases_canonicalize_to_manifest_names() -> None:
    assert canonical_company_name("BMW Group") == "BMW AG"
    assert canonical_company_name("Deutsche Telekom") == "Deutsche Telekom AG"
    assert canonical_company_name("Fresenius") == "Fresenius SE & Co. KGaA"
    assert canonical_company_name("Linde") == "Linde plc"
    assert canonical_company_name("PUMA") == "PUMA SE"
    assert canonical_company_name("RWE") == "RWE AG"
    assert canonical_company_name("SAP") == "SAP SE"
    assert canonical_company_name("Volkswagen Group") == "Volkswagen AG"
    assert canonical_company_name("thyssenkrupp") == "thyssenkrupp AG"


def test_alias_pairs_match_after_canonicalization() -> None:
    assert company_names_match("Volkswagen Group", "Volkswagen AG")
    assert company_names_match("RWE", "RWE AG")
    assert company_names_match("SAP", "SAP SE")
