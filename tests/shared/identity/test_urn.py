import pytest
from datetime import datetime
from karsa.shared.identity.urn import URN
from karsa.shared.identity.urn_builder import URNBuilder

def test_evidence_urn_parsing():
    urn_str = "evidence:idx:financials:20240101:abcd123"
    urn = URN.parse(urn_str)
    assert urn.domain == "evidence"
    assert urn.asset == "idx"
    assert urn.category == "financials"
    assert urn.timestamp_or_version == "20240101"
    assert urn.hash_val == "abcd123"
    assert str(urn) == urn_str

def test_research_urn_parsing():
    urn_str = "research:IDX:BBCA:1700000000"
    urn = URN.parse(urn_str)
    assert urn.domain == "research"
    assert urn.asset == "IDX:BBCA"
    assert urn.timestamp_or_version == "1700000000"
    assert str(urn) == urn_str

def test_thesis_urn_parsing():
    urn_str = "thesis:IDX:BBCA:v2"
    urn = URN.parse(urn_str)
    assert urn.domain == "thesis"
    assert urn.asset == "IDX:BBCA"
    assert urn.timestamp_or_version == "v2"
    assert str(urn) == urn_str

def test_urn_builder():
    dt = datetime.fromtimestamp(1700000000)
    urn = URNBuilder.build_forecast_urn("IDX:BBCA", dt)
    assert str(urn) == "forecast:IDX:BBCA:1700000000"
    
    urn2 = URNBuilder.build_evidence_urn("financials", "20240101", "abcd")
    assert str(urn2) == "evidence:idx:financials:20240101:abcd"
    
    urn3 = URNBuilder.build_research_urn("IDX:BBCA", dt)
    assert str(urn3) == "research:IDX:BBCA:1700000000"
    
    urn4 = URNBuilder.build_thesis_urn("IDX:BBCA", 2)
    assert str(urn4) == "thesis:IDX:BBCA:v2"
    
    urn5 = URNBuilder.build_decision_urn("IDX:BBCA", dt)
    assert str(urn5) == "decision:IDX:BBCA:1700000000"
