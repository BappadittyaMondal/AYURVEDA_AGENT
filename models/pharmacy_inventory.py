"""
models/pharmacy_inventory.py - Data models for Phase 48: Automated Inventory & Pharmacy Dispensation.
Tables 102 & 103: pharmacy_inventory_lots, dispensation_records.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class PharmacyLotCreate(BaseModel):
    hospital_id: str
    formulation_name: str = Field(..., description="Classical or proprietary Ayurvedic formulation name")
    batch_number: str = Field(..., description="Batch/Lot serial code")
    gs1_datamatrix_barcode: str = Field(..., description="GS1 standard 2D DataMatrix barcode representation")
    manufacturer_name: str = Field(..., description="Certified manufacturer (e.g. IMPCL, Jan Aushadhi, Kottakkal Arya Vaidya Sala)")
    stock_quantity_units: int = Field(..., ge=0, description="Available pack/unit count")
    unit_measure: str = Field("BOTTLE_60_TABS", description="Unit measure (BOTTLE, VIAL, STRIP, BOX_KG)")
    expiry_date: str = Field(..., description="Expiry date in YYYY-MM-DD")
    is_quarantined: bool = Field(False, description="Whether lot is under quarantine/hold")
    contains_schedule_e1: bool = Field(False, description="Whether lot contains Schedule E(1) poisonous substance")
    certified_shodhana_batch_code: Optional[str] = Field(None, description="Certified Shodhana purification batch identifier")


class PharmacyLotRecord(BaseModel):
    lot_id: str
    hospital_id: str
    formulation_name: str
    batch_number: str
    gs1_datamatrix_barcode: str
    manufacturer_name: str
    stock_quantity_units: int
    unit_measure: str
    expiry_date: str
    is_quarantined: bool
    contains_schedule_e1: bool = False
    certified_shodhana_batch_code: Optional[str] = None
    created_at: int


class DispensationCreate(BaseModel):
    prescription_id: str = Field(..., description="Digital e-prescription UUID")
    patient_id: str = Field(..., description="Master Patient Index ID")
    hospital_id: str = Field(..., description="Hospital UUID")
    lot_id: str = Field(..., description="Inventory lot ID being dispensed from")
    quantity_dispensed: int = Field(..., gt=0, description="Quantity to decrement from inventory")
    pharmacist_user_id: str = Field(..., description="User ID of dispensing pharmacist")
    is_pregnant: Optional[bool] = Field(None, description="Active pregnancy status")
    active_allopathic_medications: List[str] = Field(default_factory=list, description="Concurrent modern medications")
    primary_prescriber_arn: Optional[str] = Field(None, description="Prescribing NCISM Physician ARN")
    secondary_physician_countersign_arn: Optional[str] = Field(None, description="Second physician ARN for Schedule E(1) signoff")
    verified_shodhana_batch_code: Optional[str] = Field(None, description="Verified Shodhana batch reference")


class DispensationRecord(BaseModel):
    dispensation_id: str
    prescription_id: str
    patient_id: str
    hospital_id: str
    lot_id: str
    quantity_dispensed: int
    pharmacist_user_id: str
    dispensed_at: int
    remaining_stock_units: int
    safety_invariants_verified: bool = True
    two_physician_verified: bool = False
