from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VehicleListing:
    source_marketplace: Optional[str] = None
    listing_id: Optional[str] = None
    url: Optional[str] = None
    listing_fingerprint: Optional[str] = None
    brand_normalized: Optional[str] = None
    model_family_normalized: Optional[str] = None
    model_variant_normalized: Optional[str] = None
    trim_normalized: Optional[str] = None
    drivetrain_or_gearbox_normalized: Optional[str] = None
    marketing_tags_json: Optional[str] = None
    ownership_hint: Optional[str] = None
    seller_normalized: Optional[str] = None
    title_raw: Optional[str] = None
    title_harmonized: Optional[str] = None
    vehicle_type: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    first_registration: Optional[str] = None
    mileage_km: Optional[int] = None
    previous_owner_count: Optional[int] = None
    price_amount: Optional[float] = None
    price_currency: Optional[str] = None
    price_negotiable: Optional[bool] = None
    engine_displacement_cc: Optional[int] = None
    power_kw: Optional[float] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    vehicle_category: Optional[str] = None
    location_city: Optional[str] = None
    condition: Optional[str] = None
    source_image_path: Optional[str] = None
    source_image_hash: Optional[str] = None
    source_image_mime_type: Optional[str] = None
    source_image_bytes: Optional[bytes] = None
    ocr_confidence_overall: Optional[float] = None
    extraction_timestamp_utc: Optional[str] = None
    raw_payload_json: Optional[str] = None


@dataclass
class FieldExtraction:
    value: Optional[str]
    confidence: float
    raw: Optional[str] = None


@dataclass
class ExtractionResult:
    source_marketplace: Optional[str] = None
    listing_id: Optional[str] = None
    url: FieldExtraction = field(default_factory=lambda: FieldExtraction(None, 0.0))
    brand: FieldExtraction = field(default_factory=lambda: FieldExtraction(None, 0.0))
    model: FieldExtraction = field(default_factory=lambda: FieldExtraction(None, 0.0))
    year: FieldExtraction = field(default_factory=lambda: FieldExtraction(None, 0.0))
    first_registration: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    mileage_km: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    previous_owner_count: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    price_amount: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    price_currency: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    engine_displacement_cc: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    power_kw: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    fuel_type: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    transmission: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    color: FieldExtraction = field(default_factory=lambda: FieldExtraction(None, 0.0))
    vehicle_category: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    location_city: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    condition: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    vehicle_type: FieldExtraction = field(
        default_factory=lambda: FieldExtraction(None, 0.0)
    )
    ocr_text: str = ""

    def overall_confidence(self) -> float:
        extractions = [
            self.url,
            self.brand,
            self.model,
            self.year,
            self.mileage_km,
            self.price_amount,
        ]
        values = [e.confidence for e in extractions if e.value is not None]
        return sum(values) / len(values) if values else 0.0

    def to_vehicle_listing(self) -> VehicleListing:
        return VehicleListing(
            source_marketplace=self.source_marketplace,
            listing_id=self.listing_id,
            url=self.url.value,
            brand=self.brand.value,
            model=self.model.value,
            year=int(self.year.value) if self.year.value else None,
            first_registration=self.first_registration.value,
            mileage_km=int(self.mileage_km.value) if self.mileage_km.value else None,
            previous_owner_count=int(self.previous_owner_count.value)
            if self.previous_owner_count.value
            else None,
            price_amount=float(self.price_amount.value)
            if self.price_amount.value
            else None,
            price_currency=self.price_currency.value,
            engine_displacement_cc=int(self.engine_displacement_cc.value)
            if self.engine_displacement_cc.value
            else None,
            power_kw=float(self.power_kw.value) if self.power_kw.value else None,
            fuel_type=self.fuel_type.value,
            transmission=self.transmission.value,
            color=self.color.value,
            vehicle_category=self.vehicle_category.value,
            vehicle_type=self.vehicle_type.value,
            location_city=self.location_city.value,
            condition=self.condition.value,
            ocr_confidence_overall=self.overall_confidence(),
        )
