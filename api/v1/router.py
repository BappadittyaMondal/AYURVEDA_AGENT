"""API v1 unified router aggregation."""
from fastapi import APIRouter
from api.v1.agada_tantra import router as agada_tantra_router
from api.v1.ama_agni import router as ama_agni_router
from api.v1.ashtavidha import router as ashtavidha_router
from api.v1.auth import router as auth_router
from api.v1.ayush_grid import router as ayush_grid_router
from api.v1.bhaishajya_kalpana import router as bhaishajya_kalpana_router
from api.v1.clinical_trials import router as clinical_trials_router
from api.v1.dashavidha import router as dashavidha_router
from api.v1.dhatu_sarata import router as dhatu_sarata_router
from api.v1.diagnosis import router as diagnosis_router
from api.v1.dietetics import router as dietetics_router
from api.v1.disaster_recovery import router as disaster_recovery_router
from api.v1.dravyaguna import router as dravyaguna_router
from api.v1.edge_sync import router as edge_sync_router
from api.v1.emergency_transfer import router as emergency_transfer_router
from api.v1.hdi_matrix import router as hdi_router
from api.v1.health import router as health_router
from api.v1.iot_sensors import router as iot_sensors_router
from api.v1.ipd_management import router as ipd_management_router
from api.v1.jihwa import router as jihwa_router
from api.v1.kaumarbhritya import router as kaumarbhritya_router
from api.v1.kriya_kala import router as kriya_kala_router
from api.v1.manasa_roga import router as manasa_roga_router
from api.v1.marma_sharira import router as marma_sharira_router
from api.v1.morbidity_coding import router as morbidity_coding_router
from api.v1.multilingual import router as multilingual_router
from api.v1.nadi import router as nadi_router
from api.v1.nidana_panchaka import router as nidana_panchaka_router
from api.v1.opd_queue import router as opd_queue_router
from api.v1.panchakarma import router as panchakarma_router
from api.v1.paschat_karma import router as paschat_karma_router
from api.v1.patient_portal import router as patient_portal_router
from api.v1.patients import router as patients_router
from api.v1.pharmacovigilance import router as pharmacovigilance_router
from api.v1.pharmacy_inventory import router as pharmacy_inventory_router
from api.v1.practitioners import router as practitioners_router
from api.v1.prakriti import router as prakriti_router
from api.v1.production_readiness import router as production_readiness_router
from api.v1.prasuti_tantra import router as prasuti_tantra_router
from api.v1.raktamokshana import router as raktamokshana_router
from api.v1.rasa_shastra import router as rasa_shastra_router
from api.v1.rasayana_tantra import router as rasayana_tantra_router
from api.v1.roga_rogi_bala import router as roga_rogi_bala_router
from api.v1.security_hardening import router as security_hardening_router
from api.v1.shalya_tantra import router as shalya_tantra_router
from api.v1.shalya_instruments import router as shalya_instruments_router
from api.v1.shalakya_tantra import router as shalakya_tantra_router
from api.v1.srotas import router as srotas_router
from api.v1.swasthavritta import router as swasthavritta_router
from api.v1.taila_bindu import router as taila_bindu_router
from api.v1.tele_ayush import router as tele_ayush_router
from api.v1.upakarma import router as upakarma_router
from api.v1.vajikarana_tantra import router as vajikarana_tantra_router
from api.v1.vikriti import router as vikriti_router
from api.v1.vision_diagnostics import router as vision_diagnostics_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(practitioners_router)
api_v1_router.include_router(patients_router)
api_v1_router.include_router(prakriti_router)
api_v1_router.include_router(vikriti_router)
api_v1_router.include_router(ashtavidha_router)
api_v1_router.include_router(dashavidha_router)
api_v1_router.include_router(nadi_router)
api_v1_router.include_router(taila_bindu_router)
api_v1_router.include_router(jihwa_router)
api_v1_router.include_router(ama_agni_router)
api_v1_router.include_router(dhatu_sarata_router)
api_v1_router.include_router(srotas_router)
api_v1_router.include_router(kriya_kala_router)
api_v1_router.include_router(roga_rogi_bala_router)
api_v1_router.include_router(nidana_panchaka_router)
api_v1_router.include_router(morbidity_coding_router)
api_v1_router.include_router(dravyaguna_router)
api_v1_router.include_router(bhaishajya_kalpana_router)
api_v1_router.include_router(rasa_shastra_router)
api_v1_router.include_router(panchakarma_router)
api_v1_router.include_router(paschat_karma_router)
api_v1_router.include_router(upakarma_router)
api_v1_router.include_router(dietetics_router)
api_v1_router.include_router(swasthavritta_router)
api_v1_router.include_router(manasa_roga_router)
api_v1_router.include_router(shalya_tantra_router)
api_v1_router.include_router(shalakya_tantra_router)
api_v1_router.include_router(prasuti_tantra_router)
api_v1_router.include_router(kaumarbhritya_router)
api_v1_router.include_router(agada_tantra_router)
api_v1_router.include_router(rasayana_tantra_router)
api_v1_router.include_router(vajikarana_tantra_router)
api_v1_router.include_router(marma_sharira_router)
api_v1_router.include_router(shalya_instruments_router)
api_v1_router.include_router(raktamokshana_router)
api_v1_router.include_router(diagnosis_router)
api_v1_router.include_router(emergency_transfer_router)
api_v1_router.include_router(hdi_router)
api_v1_router.include_router(multilingual_router)
api_v1_router.include_router(tele_ayush_router)
api_v1_router.include_router(iot_sensors_router)
api_v1_router.include_router(vision_diagnostics_router)
api_v1_router.include_router(patient_portal_router)
api_v1_router.include_router(ayush_grid_router)
api_v1_router.include_router(edge_sync_router)
api_v1_router.include_router(pharmacovigilance_router)
api_v1_router.include_router(clinical_trials_router)
api_v1_router.include_router(ipd_management_router)
api_v1_router.include_router(opd_queue_router)
api_v1_router.include_router(pharmacy_inventory_router)
api_v1_router.include_router(disaster_recovery_router)
api_v1_router.include_router(security_hardening_router)
api_v1_router.include_router(production_readiness_router)




