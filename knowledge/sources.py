"""Curated legal snippets for offline reasoning and drafting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class LawSource:
    url: str
    title: str
    as_of: date
    summary: str
    bullet_points: List[str]
    keywords: List[str]


LAW_SOURCES: List[LawSource] = [
    LawSource(
        url="https://www.consumer.vic.gov.au/housing/renting/repairs-alterations-safety-and-pets/repairs/repairs-in-rental-properties",
        title="Repairs in rental properties - Consumer Affairs Victoria",
        as_of=date(2025, 5, 2),
        summary=(
            "Urgent repairs include essential services such as hot water, heating, cooking, serious leaks, gas and electrical faults."
            " Non-urgent repairs must be completed within 14 days after a written request."
            " Renters can arrange urgent repairs up to $2,500 if the rental provider does not act immediately and must be reimbursed within 7 days."
        ),
        bullet_points=[
            "Urgent repairs must be arranged immediately and cover essential services like hot water, heating, gas leaks, serious leaks, and dangerous electrical faults.",
            "Renters may authorise urgent repairs costing up to $2,500 if the rental provider does not respond and must be reimbursed within 7 days after giving written notice and receipts.",
            "Non-urgent repairs must be completed within 14 days of a written request, with escalation options via RDRV and VCAT.",
            "Entry for repairs requires 24 hours' notice between 8am and 6pm unless otherwise agreed for urgent situations.",
        ],
        keywords=["urgent", "hot water", "heating", "repairs", "$2,500", "7 days", "14 days", "entry"],
    ),
    LawSource(
        url="https://www.consumer.vic.gov.au/housing/renting/repairs-alterations-safety-and-pets/minimum-standards/minimum-standards-for-rental-properties",
        title="Rental properties - minimum standards - Consumer Affairs Victoria",
        as_of=date(2025, 5, 2),
        summary=(
            "Rental properties must meet minimum standards covering electrical safety, fixed heating in the main living area, secure locks, ventilation, and more."
        ),
        bullet_points=[
            "Fixed heater in the main living area required for agreements from 29 March 2021.",
            "Electrical safety and switchboard requirements apply, alongside ventilation, locks, and window coverings.",
            "Updated 2 May 2025; renters can seek repairs or compensation if minimum standards are not met.",
        ],
        keywords=["minimum standards", "heater", "electrical", "ventilation"],
    ),
    LawSource(
        url="https://www.consumer.vic.gov.au/housing/renting/rent-bond-bills-and-condition-reports/rent/rent-increases",
        title="Rent increases - Consumer Affairs Victoria",
        as_of=date(2025, 4, 24),
        summary=(
            "Rent can generally only increase once every 12 months for agreements starting on or after 19 June 2019 and requires 60 days' written notice using the prescribed CAV form."
        ),
        bullet_points=[
            "Verify that at least 12 months have passed since the last increase.",
            "Notice must give at least 60 days and use the correct Consumer Affairs Victoria form.",
            "Renters can request a CAV rent assessment if an increase seems excessive.",
        ],
        keywords=["rent", "increase", "60 days", "12 months", "assessment"],
    ),
    LawSource(
        url="https://www.consumer.vic.gov.au/housing/renting/moving-out-giving-notice-and-evictions/notice-to-vacate/notice-to-vacate-in-rental-properties",
        title="Notice to vacate in rental properties - Consumer Affairs Victoria",
        as_of=date(2025, 5, 2),
        summary=(
            "Notice to vacate periods vary by reason; some are immediate (unfit premises), others 14, 28, 60, or 90 days. Renters can challenge invalid notices."
        ),
        bullet_points=[
            "Check the stated reason matches allowable grounds and minimum notice periods.",
            "Immediate notice applies only if the property is unfit for human habitation or destroyed.",
            "Many notices require 60 days or more; renters can challenge non-compliant notices at VCAT.",
        ],
        keywords=["notice", "vacate", "eviction", "14 days", "60 days", "90 days"],
    ),
    LawSource(
        url="https://www.vcat.vic.gov.au/fees",
        title="VCAT fees",
        as_of=date(2025, 7, 1),
        summary=(
            "VCAT publishes annual fee schedules updated each 1 July. Users should consult the fee calculator rather than relying on hard-coded amounts."
        ),
        bullet_points=[
            "Use the published fee calculator or fee schedules for up-to-date amounts.",
            "Fees vary by list and applicant concession status; link renters to the official resource.",
        ],
        keywords=["vcat", "fees", "calculator"],
    ),
    LawSource(
        url="https://www.heraldsun.com.au/real-estate/victoria/melbourne/victorian-governments-rental-reforms-passed-two-years-to-come-into-effect/news-story/245c03bd10998f9f5e9b1b80f5ebc720",
        title="Victorian government rental reforms",
        as_of=date(2025, 5, 1),
        summary=(
            "Additional rental reforms are scheduled for 1 November 2025, including bans on no-fault evictions and longer notice periods. Communicate current law and upcoming changes."
        ),
        bullet_points=[
            "Highlight pending reforms effective 1 November 2025 where relevant.",
            "Clarify when guidance refers to current vs upcoming law.",
        ],
        keywords=["reform", "ban", "no-fault", "2025"],
    ),
]
