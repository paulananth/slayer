# Ontology Alignment Notes

This fixture demonstrates how the semantic-modeling skill should document FIBO-style alignment without pretending ontology terms prove warehouse constraints.

| Model element | FIBO-style concept | Evidence to verify in a real FIBO repo | Mapping confidence |
| --- | --- | --- | --- |
| `legal_entities.lei` | Legal Entity Identifier | Search FBC/BE modules for LEI and legal entity identifier definitions | High |
| `legal_entities.legal_name` | Legal Entity | Search BE legal entity classes and labels | High |
| `instruments.instrument_id` | Financial Instrument / Security | Search FBC and SEC modules for financial instrument and security | Medium |
| `instruments.issuer_lei` | Issuer role | Search SEC/FBC issuer-related object properties | Medium |
| `instruments.obligor_lei` | Obligor role | Search debt/loan obligation concepts | Medium |
| `instruments.coupon_rate` | Coupon rate | Search debt and bond terms for coupon rate | Medium |
| `instruments.maturity_date` | Maturity date | Search contract/debt maturity concepts | High |
| `positions.market_value_usd` | Market value of holding | Search market value / valuation concepts; confirm unit and date basis in data | Medium |
| `trades.notional_amount_usd` | Notional amount | Search derivatives and contract terms for notional amount | Medium |
| `risk_exposures.exposure_amount_usd` | Risk exposure | Search risk/exposure concepts; confirm local business definition | Low |

Rules enforced by the fixture:

- Ontology terms improve descriptions and synonyms.
- Physical joins still use warehouse columns such as `INSTRUMENT_ID` and `LEI`.
- Issuer, obligor, counterparty, buyer, seller, broker, and custodian are distinct roles.
- Rates, prices, balances, market values, and exposures need date-basis clarification.
- Confidence is lower when a term is local business vocabulary rather than a direct ontology match.

