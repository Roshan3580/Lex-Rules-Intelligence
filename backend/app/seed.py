"""Seed data for the demo.

This module loads three illustrative tax-rule sources (California, Texas,
New York) and a handful of normalized rules per state covering several tax
categories. The text is paraphrased / placeholder content for prototype
purposes; in production the same pipeline would ingest real PDFs and
state-government URLs. Every seeded rule still cites a source row and
snippet so the explainability story is intact.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from . import models
from .utils.chunking import chunk_text


# ---------------------------------------------------------------------------
# Source documents (paraphrased / illustrative; clearly marked as demo)
# ---------------------------------------------------------------------------


CA_TEXT = """
California Department of Tax and Fee Administration — Demo Bulletin (illustrative)

Sales and Use Tax in California.
Businesses making sales of tangible personal property in California must
register with the California Department of Tax and Fee Administration
(CDTFA) for a seller's permit before making sales. Once registered, a
business is required to file sales and use tax returns. Most businesses
file quarterly. Returns and payments are generally due by the last day of
the month following the end of the reporting period (for example, the
Q1 return covering January through March is due by April 30).
Remote sellers and marketplace facilitators with more than $500,000 of
combined sales of tangible personal property delivered into California in
the current or preceding calendar year must register and collect tax.
Use tax is owed by purchasers when sales tax has not been collected.

Personal Income Tax Withholding in California.
Employers paying wages for services performed in California must
withhold California personal income tax. Employers register with the
Employment Development Department (EDD) and use Form DE 4 to determine
employee withholding. Employers must file the quarterly contribution
return and report of wages (Form DE 9 and DE 9C) by April 30, July 31,
October 31, and January 31. Failure to file or pay on time is subject
to penalties and interest.

Corporate Franchise / Income Tax in California.
Corporations doing business in California are subject to the California
corporation franchise tax or income tax administered by the Franchise
Tax Board (FTB). The minimum franchise tax is generally $800 per year
after the first taxable year. The corporation tax return (Form 100) is
due on the 15th day of the 4th month after the close of the taxable
year (April 15 for calendar-year filers). Estimated payments are
required quarterly.
"""

TX_TEXT = """
Texas Comptroller of Public Accounts — Demo Bulletin (illustrative)

Sales and Use Tax in Texas.
Texas imposes a 6.25% state sales and use tax on sales, leases, and
rentals of most goods, as well as taxable services. Local taxing
jurisdictions may add up to 2% in additional sales and use tax for a
combined maximum rate of 8.25%. Sellers must obtain a sales and use
tax permit from the Texas Comptroller before doing business. Sales tax
returns are due monthly, quarterly, or annually depending on the amount
of tax owed. Monthly returns are due on the 20th day of the month
following the reporting period.

Texas Franchise Tax.
Most taxable entities formed in or doing business in Texas owe the
franchise tax (commonly called the "margin tax"). The annual franchise
tax report is due May 15. Entities below the no-tax-due threshold may
file a No Tax Due Report. The Public Information Report (Form 05-102)
or Ownership Information Report is required as part of the filing.

Texas Payroll / Unemployment Tax.
Texas does not impose a state personal income tax, so there is no
state employer withholding. However, employers must pay state
unemployment insurance (SUI) tax to the Texas Workforce Commission.
Quarterly Wage Reports are due by the last day of the month following
the end of each calendar quarter (April 30, July 31, October 31,
January 31).
"""

NY_TEXT = """
New York State Department of Taxation and Finance — Demo Bulletin (illustrative)

New York Sales and Use Tax.
Vendors making taxable sales in New York must register with the
Department of Taxation and Finance for a Certificate of Authority
before making sales. Sales tax returns are filed quarterly (Form
ST-100), annually, or on a part-quarterly (monthly) basis depending on
the vendor's taxable sales volume. Quarterly returns are due on the
20th of the month after the end of each sales tax quarter (the New
York sales tax quarters end February, May, August, and November).
Marketplace providers and remote sellers exceeding $500,000 in gross
receipts and 100 transactions must collect.

New York Employer Withholding.
Employers required to withhold New York State personal income tax must
register and file Form NYS-45 (Quarterly Combined Withholding, Wage
Reporting, and Unemployment Insurance Return) by the last day of the
month following the end of each calendar quarter. New employees must
complete Form IT-2104.

New York Corporate Franchise Tax (Article 9-A).
A general business corporation doing business in New York is subject
to the corporation franchise tax. Form CT-3 is filed annually. The
return is due by the 15th day of the 4th month following the close of
the corporation's tax year (April 15 for calendar-year filers).
Estimated tax payments are required.
"""


SEED_SOURCES = [
    {
        "state": "California",
        "name": "CDTFA / EDD / FTB Demo Bulletin (illustrative)",
        "url": "https://example.gov/ca/tax/demo",
        "text": CA_TEXT,
    },
    {
        "state": "Texas",
        "name": "Texas Comptroller Demo Bulletin (illustrative)",
        "url": "https://example.gov/tx/tax/demo",
        "text": TX_TEXT,
    },
    {
        "state": "New York",
        "name": "NYS Tax & Finance Demo Bulletin (illustrative)",
        "url": "https://example.gov/ny/tax/demo",
        "text": NY_TEXT,
    },
]


# ---------------------------------------------------------------------------
# Pre-baked normalized rules
# ---------------------------------------------------------------------------

# Fixed titles used to idempotently upsert Submission Validator demos.
_CA_ENFORCEMENT_DEMO_RULE_TITLES = (
    "CA Sales Tax — CDTFA-401-A required at submission (demo)",
    "CA Sales Tax — LLC / high-amount Schedule R (demo)",
)

_REVIEW_QUEUE_DEMO_RULE_TITLES = (
    "California use tax — occasional sale exemption (needs review)",
    "Texas sales tax — marketplace facilitator registration (auto-validated)",
    "New York ST-100 — part-quarterly filing threshold (draft)",
)


def _resolve_state_source(db: Session, state: str) -> models.Source | None:
    spec = next((x for x in SEED_SOURCES if x["state"] == state), None)
    if spec is None:
        return None
    hit = db.query(models.Source).filter(models.Source.url == spec["url"]).first()
    if hit is not None:
        return hit
    return (
        db.query(models.Source)
        .filter(models.Source.state == state)
        .order_by(models.Source.created_at.asc())
        .first()
    )


def _review_queue_demo_rules(
    ca: models.Source, tx: models.Source, ny: models.Source
) -> list[models.Rule]:
    """Illustrative extracted rules awaiting human review (demo only)."""
    return [
        models.Rule(
            state="California",
            tax_category="sales_tax",
            rule_title=_REVIEW_QUEUE_DEMO_RULE_TITLES[0],
            rule_summary=(
                "Extracted rule: purchasers may owe use tax on occasional sales "
                "when sales tax was not collected — confidence below publish threshold."
            ),
            detailed_rule=(
                "Illustrative extraction pending review. Verify exemption thresholds "
                "and required documentation against the source bulletin before approving."
            ),
            conditions=["Occasional or casual sale without collected sales tax"],
            required_actions=["Assess use tax liability", "Retain purchase records"],
            required_forms=[],
            deadlines=[],
            exceptions=["Specific occasional-sale exemptions may apply"],
            source_id=ca.id,
            source_url=ca.url,
            source_document_name=ca.name,
            source_snippet=(
                "Use tax is owed by purchasers when sales tax has not been collected..."
            ),
            effective_date="2024-01-01",
            confidence_score=0.58,
            review_status="needs_review",
            extraction_method="seed",
        ),
        models.Rule(
            state="Texas",
            tax_category="sales_tax",
            rule_title=_REVIEW_QUEUE_DEMO_RULE_TITLES[1],
            rule_summary=(
                "Extracted rule: marketplace facilitators must collect Texas sales "
                "tax when facilitating third-party sales — auto-validated pending publish."
            ),
            detailed_rule=(
                "Illustrative auto-validated extraction. Confirm facilitator registration "
                "requirements and filing cadence with the Comptroller bulletin."
            ),
            conditions=["Acting as marketplace facilitator for Texas sales"],
            required_actions=[
                "Register as marketplace facilitator",
                "Collect and remit applicable sales tax",
            ],
            required_forms=["Form 01-114 (Sales and Use Tax Return)"],
            deadlines=["20th of month following reporting period (monthly filers)"],
            exceptions=None,
            source_id=tx.id,
            source_url=tx.url,
            source_document_name=tx.name,
            source_snippet=(
                "Sellers must obtain a sales and use tax permit from the Texas "
                "Comptroller before doing business..."
            ),
            effective_date="2024-01-01",
            confidence_score=0.74,
            review_status="auto_validated",
            extraction_method="seed",
        ),
        models.Rule(
            state="New York",
            tax_category="sales_tax",
            rule_title=_REVIEW_QUEUE_DEMO_RULE_TITLES[2],
            rule_summary=(
                "Draft extraction: vendors above part-quarterly thresholds must file "
                "ST-100 on a monthly cadence — awaiting reviewer edit."
            ),
            detailed_rule=(
                "Illustrative draft rule from pasted bulletin text. Review filing "
                "frequency thresholds and form references before approval."
            ),
            conditions=["Taxable sales volume triggers part-quarterly (monthly) filing"],
            required_actions=["File Form ST-100 on assigned cadence"],
            required_forms=["Form ST-100"],
            deadlines=["20th of month after each NY sales tax quarter end"],
            exceptions=["Annual filing for lower-volume vendors"],
            source_id=ny.id,
            source_url=ny.url,
            source_document_name=ny.name,
            source_snippet=(
                "Sales tax returns are filed quarterly (Form ST-100), annually, "
                "or on a part-quarterly (monthly) basis depending on the "
                "vendor's taxable sales volume."
            ),
            effective_date="2024-01-01",
            confidence_score=0.52,
            review_status="draft",
            extraction_method="seed",
        ),
    ]


def _ca_enforcement_demo_rules(source: models.Source) -> list[models.Rule]:
    """submission-stage demos for risky CA preset (documents + conditional Schedule R)."""
    return [
        models.Rule(
            state="California",
            tax_category="sales_tax",
            workflow_stage="submission",
            rule_category="enforcement_demo",
            rule_title="CA Sales Tax — CDTFA-401-A required at submission (demo)",
            rule_summary=(
                "Demo gate: portal submissions for California sales tax at the "
                "submission stage must include CDTFA-401-A."
            ),
            detailed_rule=(
                "Illustrative enforcement rule for demos. Attach CDTFA-401-A "
                "(Sales and Use Tax Supplement) before submitting."
            ),
            conditions=["California sales tax submission via portal"],
            required_actions=["Attach CDTFA-401-A before submission"],
            required_forms=[],
            required_documentation=["CDTFA-401-A"],
            deadlines=[],
            exceptions=None,
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Demo: California sales tax submissions must include form "
                "CDTFA-401-A (illustrative)."
            ),
            effective_date="2024-01-01",
            confidence_score=0.91,
            review_status="published",
            extraction_method="seed",
        ),
        models.Rule(
            state="California",
            tax_category="sales_tax",
            workflow_stage="submission",
            rule_category="enforcement_demo",
            rule_title="CA Sales Tax — LLC / high-amount Schedule R (demo)",
            rule_summary=(
                "Demo threshold rule: LLC filers with taxable amount over $10,000 "
                "must include Schedule R (demo form name)."
            ),
            detailed_rule=(
                "Illustrative JSON condition_logic: entity_type LLC and amount "
                "greater than 10000 triggers Schedule R attachment."
            ),
            conditions=["LLC with amount over $10,000"],
            required_actions=["Attach Schedule R for high-amount LLC filings"],
            required_forms=["Schedule R (demo)"],
            required_documentation=[],
            deadlines=[],
            exceptions=None,
            condition_logic=json.dumps(
                {
                    "op": "and",
                    "items": [
                        {
                            "op": "equals",
                            "field": "entity_type",
                            "value": "LLC",
                        },
                        {
                            "op": "greater_than",
                            "field": "amount",
                            "value": 10000,
                        },
                    ],
                }
            ),
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Demo: combined LLC + amount threshold requires Schedule R "
                "(illustrative)."
            ),
            effective_date="2024-01-01",
            confidence_score=0.89,
            review_status="published",
            extraction_method="seed",
        ),
    ]


def _ca_rules(source: models.Source) -> list[models.Rule]:
    return [
        models.Rule(
            state="California",
            tax_category="sales_tax",
            rule_title="California Sales Tax — Seller's Permit & Filing",
            rule_summary=(
                "Businesses selling tangible personal property in California must "
                "register with CDTFA for a seller's permit and file sales and use "
                "tax returns, generally on a quarterly cadence."
            ),
            detailed_rule=(
                "A seller's permit must be obtained from the California Department "
                "of Tax and Fee Administration prior to making sales. Most "
                "businesses file quarterly, with returns and payments due by the "
                "last day of the month following the end of the reporting period. "
                "Remote sellers and marketplace facilitators meeting the economic "
                "nexus threshold ($500,000 of California-delivered sales) must "
                "also register and collect."
            ),
            conditions=[
                "Selling tangible personal property in California",
                "Remote seller/marketplace facilitator over $500,000 in California sales",
            ],
            required_actions=[
                "Register with CDTFA for a seller's permit",
                "Collect sales and use tax",
                "File quarterly sales and use tax returns",
            ],
            required_forms=["CDTFA Seller's Permit", "CDTFA-401 (Sales/Use Tax Return)"],
            deadlines=["Quarterly: last day of month following the quarter (e.g., April 30 for Q1)"],
            exceptions=["Occasional/casual sales may be exempt under specific conditions"],
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Businesses making sales of tangible personal property in "
                "California must register with the California Department of Tax "
                "and Fee Administration (CDTFA) for a seller's permit before "
                "making sales..."
            ),
            effective_date="2024-01-01",
            confidence_score=0.9,
            review_status="published",
            extraction_method="seed",
        ),
        models.Rule(
            state="California",
            tax_category="withholding",
            rule_title="California Employer Withholding — DE 9 / DE 9C",
            rule_summary=(
                "Employers paying wages for services performed in California must "
                "withhold California PIT and file the quarterly DE 9 / DE 9C with "
                "the EDD."
            ),
            detailed_rule=(
                "Employers register with the Employment Development Department, "
                "use Form DE 4 to determine each employee's withholding, and file "
                "the quarterly contribution return and report of wages (Form DE 9 "
                "and DE 9C) on April 30, July 31, October 31, and January 31."
            ),
            conditions=["Paying wages for services performed in California"],
            required_actions=[
                "Register with EDD",
                "Withhold California PIT from wages",
                "File DE 9 and DE 9C quarterly",
            ],
            required_forms=["Form DE 4", "Form DE 9", "Form DE 9C"],
            deadlines=["April 30", "July 31", "October 31", "January 31"],
            exceptions=None,
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Employers must file the quarterly contribution return and "
                "report of wages (Form DE 9 and DE 9C) by April 30, July 31, "
                "October 31, and January 31."
            ),
            effective_date="2024-01-01",
            confidence_score=0.92,
            review_status="published",
            extraction_method="seed",
        ),
        models.Rule(
            state="California",
            tax_category="corporate_tax",
            rule_title="California Corporate Franchise / Income Tax — Form 100",
            rule_summary=(
                "Corporations doing business in California file Form 100 with the "
                "Franchise Tax Board and owe at least the $800 minimum franchise "
                "tax annually after the first taxable year."
            ),
            detailed_rule=(
                "The corporation tax return (Form 100) is due on the 15th day of "
                "the 4th month after the close of the taxable year (April 15 for "
                "calendar-year filers). Quarterly estimated payments are required."
            ),
            conditions=["Corporation doing business in California"],
            required_actions=[
                "File Form 100 annually with FTB",
                "Make quarterly estimated payments",
                "Pay the $800 minimum franchise tax (after first year)",
            ],
            required_forms=["Form 100"],
            deadlines=["April 15 (calendar-year filers)"],
            exceptions=["First-year exemption from the $800 minimum tax for some entities"],
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "The corporation tax return (Form 100) is due on the 15th day of "
                "the 4th month after the close of the taxable year."
            ),
            effective_date="2024-01-01",
            confidence_score=0.88,
            review_status="approved",
            extraction_method="seed",
        ),
        *_ca_enforcement_demo_rules(source),
    ]


def _tx_rules(source: models.Source) -> list[models.Rule]:
    return [
        models.Rule(
            state="Texas",
            tax_category="sales_tax",
            rule_title="Texas Sales and Use Tax — Permit & Monthly Filing",
            rule_summary=(
                "Texas imposes a 6.25% state sales and use tax (up to 8.25% with "
                "local). Sellers must obtain a sales tax permit from the Texas "
                "Comptroller; monthly returns are due on the 20th of the following "
                "month."
            ),
            detailed_rule=(
                "Sellers must register with the Texas Comptroller before doing "
                "business. Filing frequency (monthly, quarterly, annual) depends "
                "on tax owed; monthly returns are due on the 20th day of the "
                "month following the reporting period."
            ),
            conditions=["Selling taxable goods or services in Texas"],
            required_actions=[
                "Apply for a Texas sales and use tax permit",
                "Collect state + applicable local sales and use tax",
                "File sales tax returns on assigned cadence",
            ],
            required_forms=["Form 01-114 (Sales and Use Tax Return)"],
            deadlines=["20th of month following reporting period (monthly filers)"],
            exceptions=["Occasional sales", "Resale and exemption certificates"],
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Texas imposes a 6.25% state sales and use tax... Monthly returns "
                "are due on the 20th day of the month following the reporting "
                "period."
            ),
            effective_date="2024-01-01",
            confidence_score=0.93,
            review_status="published",
            extraction_method="seed",
        ),
        models.Rule(
            state="Texas",
            tax_category="franchise_tax",
            rule_title="Texas Franchise (Margin) Tax — Annual Report",
            rule_summary=(
                "Most taxable entities formed in or doing business in Texas owe "
                "the franchise (margin) tax. The annual report is due May 15."
            ),
            detailed_rule=(
                "Entities below the no-tax-due threshold may file a No Tax Due "
                "Report. The Public Information Report (Form 05-102) or Ownership "
                "Information Report is required as part of the filing."
            ),
            conditions=["Taxable entity formed in or doing business in Texas"],
            required_actions=[
                "File Texas franchise tax report",
                "File Public Information Report (Form 05-102) or Ownership Information Report",
            ],
            required_forms=["Form 05-158 / 05-169", "Form 05-102"],
            deadlines=["May 15 annually"],
            exceptions=["No Tax Due Report for entities under threshold"],
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Most taxable entities formed in or doing business in Texas owe "
                "the franchise tax (commonly called the margin tax). The annual "
                "franchise tax report is due May 15."
            ),
            effective_date="2024-01-01",
            confidence_score=0.9,
            review_status="published",
            extraction_method="seed",
        ),
        models.Rule(
            state="Texas",
            tax_category="payroll_tax",
            rule_title="Texas Unemployment Insurance — Quarterly Wage Report",
            rule_summary=(
                "Texas has no state income tax, so no state withholding. "
                "Employers do owe SUI tax to the Texas Workforce Commission and "
                "file quarterly wage reports."
            ),
            detailed_rule=(
                "Quarterly Wage Reports are due by the last day of the month "
                "following the end of each calendar quarter (April 30, July 31, "
                "October 31, January 31)."
            ),
            conditions=["Liable employer under Texas Unemployment Compensation Act"],
            required_actions=[
                "Register with Texas Workforce Commission",
                "Pay state unemployment insurance tax",
                "File Quarterly Wage Report",
            ],
            required_forms=["Texas Workforce Commission Quarterly Wage Report"],
            deadlines=["April 30", "July 31", "October 31", "January 31"],
            exceptions=None,
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Texas does not impose a state personal income tax... Quarterly "
                "Wage Reports are due by the last day of the month following the "
                "end of each calendar quarter."
            ),
            effective_date="2024-01-01",
            confidence_score=0.85,
            review_status="approved",
            extraction_method="seed",
        ),
    ]


def _ny_rules(source: models.Source) -> list[models.Rule]:
    return [
        models.Rule(
            state="New York",
            tax_category="sales_tax",
            rule_title="New York Sales Tax — Certificate of Authority & ST-100",
            rule_summary=(
                "Vendors making taxable sales in New York must register for a "
                "Certificate of Authority and file Form ST-100 quarterly (or "
                "annual / part-quarterly based on volume)."
            ),
            detailed_rule=(
                "Quarterly returns (Form ST-100) are due on the 20th of the "
                "month after the end of each sales tax quarter (NY sales tax "
                "quarters end February, May, August, and November). Marketplace "
                "providers and remote sellers exceeding $500,000 in gross "
                "receipts and 100 transactions must collect."
            ),
            conditions=[
                "Making taxable sales in New York",
                "Marketplace provider/remote seller over $500,000 + 100 transactions",
            ],
            required_actions=[
                "Register for a Certificate of Authority",
                "Collect NY state and local sales tax",
                "File Form ST-100 quarterly",
            ],
            required_forms=["Certificate of Authority", "Form ST-100"],
            deadlines=["20th of month after each NY sales tax quarter end (Mar 20, Jun 20, Sep 20, Dec 20)"],
            exceptions=["Annual or part-quarterly filing thresholds"],
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Sales tax returns are filed quarterly (Form ST-100), annually, "
                "or on a part-quarterly (monthly) basis depending on the "
                "vendor's taxable sales volume."
            ),
            effective_date="2024-01-01",
            confidence_score=0.92,
            review_status="published",
            extraction_method="seed",
        ),
        models.Rule(
            state="New York",
            tax_category="withholding",
            rule_title="New York Employer Withholding — Form NYS-45",
            rule_summary=(
                "Employers required to withhold NY State personal income tax "
                "must file Form NYS-45 quarterly, combining withholding, wage "
                "reporting, and unemployment insurance."
            ),
            detailed_rule=(
                "Form NYS-45 is due by the last day of the month following the "
                "end of each calendar quarter. New employees must complete Form "
                "IT-2104 to determine New York withholding allowances."
            ),
            conditions=["Employer paying wages subject to NY withholding"],
            required_actions=[
                "Withhold NY State personal income tax from wages",
                "File Form NYS-45 quarterly",
                "Have new hires complete Form IT-2104",
            ],
            required_forms=["Form NYS-45", "Form IT-2104"],
            deadlines=["April 30", "July 31", "October 31", "January 31"],
            exceptions=None,
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Employers required to withhold New York State personal income "
                "tax must register and file Form NYS-45 ... by the last day of "
                "the month following the end of each calendar quarter."
            ),
            effective_date="2024-01-01",
            confidence_score=0.93,
            review_status="published",
            extraction_method="seed",
        ),
        models.Rule(
            state="New York",
            tax_category="corporate_tax",
            rule_title="New York Corporate Franchise Tax (Article 9-A) — Form CT-3",
            rule_summary=(
                "A general business corporation doing business in New York is "
                "subject to the Article 9-A corporation franchise tax and files "
                "Form CT-3 annually."
            ),
            detailed_rule=(
                "The return is due by the 15th day of the 4th month following "
                "the close of the corporation's tax year (April 15 for "
                "calendar-year filers). Estimated tax payments are required."
            ),
            conditions=["General business corporation doing business in New York"],
            required_actions=[
                "File Form CT-3 annually",
                "Make required estimated tax payments",
            ],
            required_forms=["Form CT-3"],
            deadlines=["April 15 (calendar-year filers)"],
            exceptions=["S corporations file Form CT-3-S"],
            source_id=source.id,
            source_url=source.url,
            source_document_name=source.name,
            source_snippet=(
                "Form CT-3 is filed annually. The return is due by the 15th day "
                "of the 4th month following the close of the corporation's tax "
                "year."
            ),
            effective_date="2024-01-01",
            confidence_score=0.9,
            review_status="published",
            extraction_method="seed",
        ),
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _resolve_ca_demo_source(db: Session) -> models.Source:
    """Source row for tying demo enforcement rules (reuse seed bulletin when possible)."""
    spec = next(x for x in SEED_SOURCES if x["state"] == "California")
    hit = db.query(models.Source).filter(models.Source.url == spec["url"]).first()
    if hit is not None:
        return hit
    fb = (
        db.query(models.Source)
        .filter(models.Source.state == "California")
        .order_by(models.Source.created_at.asc())
        .first()
    )
    if fb is not None:
        return fb
    src = models.Source(
        source_type="text",
        name=spec["name"],
        url=spec["url"],
        state=spec["state"],
        tax_category=None,
        raw_text=spec["text"],
        status="processed",
        meta={"seeded": True, "demo_enforcement_source": True},
    )
    db.add(src)
    db.flush()
    return src


def ensure_demo_review_queue_rules(db: Session) -> int:
    """Ensure human-review demo rows exist for the Review Queue UI."""
    have = (
        db.query(models.Rule.rule_title)
        .filter(models.Rule.rule_title.in_(_REVIEW_QUEUE_DEMO_RULE_TITLES))
        .all()
    )
    have_set = {r[0] for r in have}
    missing_titles = [t for t in _REVIEW_QUEUE_DEMO_RULE_TITLES if t not in have_set]
    if not missing_titles:
        return 0

    ca = _resolve_state_source(db, "California")
    tx = _resolve_state_source(db, "Texas")
    ny = _resolve_state_source(db, "New York")
    if not ca or not tx or not ny:
        return 0

    by_title = {r.rule_title: r for r in _review_queue_demo_rules(ca, tx, ny)}
    added = 0
    for title in missing_titles:
        db.add(by_title[title])
        added += 1
    db.commit()
    return added


def ensure_demo_enforcement_rules(db: Session) -> int:
    """Ensure Submission Validator CA demos exist even when the DB already had rules.

    ``seed_if_empty`` intentionally skips inserts when ``rules.count() > 0``, but
    those earlier rows are often ingestion rules scoped to intake with non-JSON
    ``condition_logic`` — they never participate in submission-stage enforcement.
    """
    have = (
        db.query(models.Rule.rule_title)
        .filter(models.Rule.rule_title.in_(_CA_ENFORCEMENT_DEMO_RULE_TITLES))
        .all()
    )
    have_set = {r[0] for r in have}
    missing_titles = [t for t in _CA_ENFORCEMENT_DEMO_RULE_TITLES if t not in have_set]
    if not missing_titles:
        return 0
    src = _resolve_ca_demo_source(db)
    by_title = {r.rule_title: r for r in _ca_enforcement_demo_rules(src)}
    added = 0
    for title in missing_titles:
        db.add(by_title[title])
        added += 1
    db.commit()
    return added


def seed_if_empty(db: Session) -> int:
    """Insert demo sources/chunks/rules iff no rules exist yet. Returns count."""
    if db.query(models.Rule).count() > 0:
        return 0

    total_rules = 0
    for spec in SEED_SOURCES:
        source = models.Source(
            source_type="text",
            name=spec["name"],
            url=spec["url"],
            state=spec["state"],
            tax_category=None,
            raw_text=spec["text"],
            status="processed",
            meta={"seeded": True},
        )
        db.add(source)
        db.flush()

        for i, c in enumerate(chunk_text(spec["text"])):
            db.add(
                models.SourceChunk(
                    source_id=source.id,
                    chunk_index=i,
                    text=c,
                    state=source.state,
                )
            )

        if spec["state"] == "California":
            rules = _ca_rules(source)
        elif spec["state"] == "Texas":
            rules = _tx_rules(source)
        else:
            rules = _ny_rules(source)
        for r in rules:
            db.add(r)
            total_rules += 1

    db.commit()
    return total_rules
