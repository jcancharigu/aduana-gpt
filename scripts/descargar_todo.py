import requests
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE    = "https://www.sunat.gob.pe"
BASE_NA = BASE + "/legislacion/procedim/normasadua/normasociada/"

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ═══════════════════════════════════════════════════════════════
# SECCION 1: DOCUMENTOS FIJOS (normativa principal)
# ═══════════════════════════════════════════════════════════════
DOCUMENTOS_FIJOS = [

    # NORMAS LEGALES PRINCIPALES
    {"nombre": "gja01_ley_procedimiento_administrativo",     "url": BASE + "/legislacion/procedim/normasadua/gja-01normasoc.htm",                                         "coleccion": "normas_legales",               "descripcion": "Ley 27444 - Procedimiento Administrativo General"},
    {"nombre": "gja03_ley_general_aduanas_dl1053",           "url": BASE + "/legislacion/procedim/normasadua/gja-03normasoc.htm",                                         "coleccion": "normas_legales",               "descripcion": "Ley General de Aduanas - DL 1053"},
    {"nombre": "gja05_ley_28008_delitos_aduaneros",          "url": BASE + "/legislacion/procedim/normasadua/gja-05normasoc.htm",                                         "coleccion": "normas_legales",               "descripcion": "Ley 28008 - Delitos Aduaneros"},

    # NORMAS ASOCIADAS VIGENTES - GJA-01
    {"nombre": "gja_00_01_ley_transparencia_tuo",            "url": BASE_NA + "gja-00.01.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 021-2019-JUS - TUO Ley Transparencia"},
    {"nombre": "gja_00_02_reglamento_transparencia_2024",    "url": BASE_NA + "gja-00.02.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 007-2024-JUS - Reglamento Ley Transparencia"},
    {"nombre": "gja_00_03_ley_etica_funcion_publica",        "url": BASE_NA + "gja-00.03.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "Ley 27815 - Codigo de Etica Funcion Publica"},
    {"nombre": "gja_00_13_reglamento_ley_29091",             "url": BASE_NA + "gja-00.13.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 004-2008-PCM - Reglamento Ley 29091"},
    {"nombre": "gja_00_20_excepcion_reserva_tributaria",     "url": BASE_NA + "gja-00.20.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 226-2009-EF - Excepcion Reserva Tributaria"},

    # NORMAS ASOCIADAS VIGENTES - GJA-03
    {"nombre": "gja_00_04_reglamento_ley_general_aduanas",   "url": BASE_NA + "gja-00.04.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 010-2009-EF - Reglamento Ley General de Aduanas"},
    {"nombre": "gja_00_05_tabla_sanciones_aduanas",          "url": BASE_NA + "gja-00.05.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 418-2019-EF - Tabla de Sanciones"},
    {"nombre": "gja_00_06_reglamento_equipaje_menaje",       "url": BASE_NA + "gja-00.06.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 182-2013-EF - Reglamento Equipaje y Menaje"},
    {"nombre": "gja_00_07_reglamento_envios_postales",       "url": BASE_NA + "gja-00.07.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 244-2013-EF - Reglamento Envios Postales"},
    {"nombre": "gja_00_08_reglamento_drawback",              "url": BASE_NA + "gja-00-08.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 104-95-EF - Reglamento Drawback"},
    {"nombre": "gja_00_10_ley_migrante_retornado",           "url": BASE_NA + "gja-00.10.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "Ley 30001 - Reinsercion Economica Migrante Retornado"},
    {"nombre": "gja_00_14_ley_mercancias_donadas",           "url": BASE_NA + "gja-00.14.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "Ley 28905 - Facilitacion Despacho Mercancias Donadas"},
    {"nombre": "gja_00_19_reglamento_envios_entrega_rapida", "url": BASE_NA + "gja-00.19.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 192-2020-EF - Reglamento Envios Entrega Rapida"},
    {"nombre": "gja_00_21_reglamento_operador_economico",    "url": BASE_NA + "gja-00.21.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 184-2016-EF - Reglamento Certificacion OEA"},
    {"nombre": "gja_00_22_reglamento_dinero_efectivo",       "url": BASE_NA + "gja-00.22.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 195-2013-EF - Reglamento Declaracion Dinero Efectivo"},
    {"nombre": "gja_00_25_reglamento_vehiculos_turismo",     "url": BASE_NA + "gja-00.25.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 076-2017-EF - Reglamento Vehiculos Turismo"},
    {"nombre": "gja_00_28_ley_facilitacion_eventos",         "url": BASE_NA + "gja-00.28.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "Ley 31816 - Facilitacion Aduanera Eventos Internacionales"},
    {"nombre": "gja_00_29_ley_modifica_migrante_retornado",  "url": BASE_NA + "gja-00.29.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "Ley 31827 - Modifica Ley Reinsercion Migrante Retornado"},

    # NORMAS ASOCIADAS VIGENTES - GJA-05
    {"nombre": "gja_00_09_reglamento_ley_28008",             "url": BASE_NA + "gja-00.09.htm",                                                                           "coleccion": "normas_legales",               "descripcion": "DS 121-2003-EF - Reglamento Ley 28008"},

    # PROCEDIMIENTOS DE DESPACHO - GENERALES
    {"nombre": "despa_pg01_importacion_consumo",             "url": BASE + "/legislacion/procedim/despacho/importacion/importac/procGeneral/despa-pg.01.htm",             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.01 - Importacion para el Consumo"},
    {"nombre": "despa_pg02_exportacion_definitiva",          "url": BASE + "/legislacion/procedim/despacho/exportacion/exportac/procGeneral/despa-pg.02.htm",             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.02 - Exportacion Definitiva"},
    {"nombre": "despa_pg03_deposito_aduanero",               "url": BASE + "/legislacion/procedim/despacho/deposito/deposito/procGeneral/despa-pg.03.htm",                "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.03 - Deposito Aduanero"},
    {"nombre": "despa_pg04_admision_temporal_reexportacion", "url": BASE + "/legislacion/procedim/despacho/importacion/adTemporalR/procGeneral/despa-pg.04.htm",          "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.04 - Admision Temporal Reexportacion"},
    {"nombre": "despa_pg05_exportacion_temporal",            "url": BASE + "/legislacion/procedim/despacho/exportacion/exTemporal/procGeneral/despa-pg.05.htm",           "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.05 - Exportacion Temporal"},
    {"nombre": "despa_pg06_admision_temporal_perfeccionamiento","url": BASE + "/legislacion/procedim/despacho/perfeccionam/adTemporal/procGeneral/despa-pg.06.htm",       "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.06 - Admision Temporal Perfeccionamiento"},
    {"nombre": "despa_pg07_drawback",                        "url": BASE + "/legislacion/procedim/despacho/perfeccionam/drawback/procGeneral/despa-pg.07.htm",            "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.07 - Drawback"},
    {"nombre": "despa_pg08_transito_aduanero",               "url": BASE + "/legislacion/procedim/despacho/transito/transito/procGeneral/despa-pg.08.htm",                "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.08 - Transito Aduanero"},
    {"nombre": "despa_pg09_manifiesto_carga",                "url": BASE + "/legislacion/procedim/despacho/manifiestos/procGeneral/despa-pg.09.htm",                      "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.09 - Manifiesto de Carga"},
    {"nombre": "despa_pg10_reposicion_mercancias",           "url": BASE + "/legislacion/procedim/despacho/perfeccionam/reposMercan/procGeneral/despa-pg.10.htm",         "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.10 - Reposicion Mercancias Franquicia"},
    {"nombre": "despa_pg11_transbordo",                      "url": BASE + "/legislacion/procedim/despacho/transito/transbordo/procGeneral/despa-pg.11.htm",              "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.11 - Transbordo"},
    {"nombre": "despa_pg12_reembarque",                      "url": BASE + "/legislacion/procedim/despacho/transito/reembarque/procGeneral/despa-pg.12.htm",              "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.12 - Reembarque"},
    {"nombre": "despa_pg13_envios_postales",                 "url": BASE + "/legislacion/procedim/despacho/especiales/consecPostal/procGeneral/despa-pg.13.htm",          "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.13 - Envios Postales"},
    {"nombre": "despa_pg15_ferias_exposiciones",             "url": BASE + "/legislacion/procedim/despacho/especiales/ferias/procGeneral/despa-pg.15.htm",                "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.15 - Ferias Exposiciones"},
    {"nombre": "despa_pg16_vehiculos_turismo",               "url": BASE + "/legislacion/procedim/despacho/especiales/vehiculos/procGeneral/despa-pg.16.htm",             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.16 - Vehiculos para Turismo"},
    {"nombre": "despa_pg17_duty_free",                       "url": BASE + "/legislacion/procedim/despacho/especiales/duttyFree/procGeneral/despa-pg.17.htm",             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.17 - Duty Free"},
    {"nombre": "despa_pg24_operadores_oce",                  "url": BASE + "/legislacion/procedim/despacho/operadores/procGeneral/despa-pg.24.htm",                       "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.24 - Autorizacion Operadores OCE"},
    {"nombre": "despa_pg25_mensajeria_internacional",        "url": BASE + "/legislacion/procedim/despacho/especiales/mensajeria/procGeneral/despa-pg.25.htm",            "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.25 - Mensajeria Internacional"},
    {"nombre": "despa_pg26_reimportacion",                   "url": BASE + "/legislacion/procedim/despacho/importacion/reimportac/procGeneral/despa-pg.26.htm",           "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.26 - Reimportacion"},
    {"nombre": "despa_pg27_transito_internacional",          "url": BASE + "/legislacion/procedim/despacho/transitoInt/procGeneral/despa-pg.27.htm",                      "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.27 - Transito Internacional CAN-ALADI"},
    {"nombre": "despa_pg28_entrega_rapida_courier",          "url": BASE + "/legislacion/procedim/despacho/especiales/envioEntRap/procGeneral/despa-pg.28.htm",           "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.28 - Envios Entrega Rapida Courier"},
    {"nombre": "despa_pg29_operador_economico_autorizado",   "url": BASE + "/legislacion/procedim/despacho/operadores/certifiOperador/procGeneral/despa-pg.29.htm",       "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PG.29 - Operador Economico Autorizado OEA"},

    # PROCEDIMIENTOS DE DESPACHO - ESPECIFICOS CONOCIDOS
    {"nombre": "despa_pe0003_reconocimiento_fisico",         "url": BASE + "/legislacion/procedim/despacho/procAsociados/despa-pe.00.03.htm",                             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.00.03 - Reconocimiento Fisico y Muestras"},
    {"nombre": "despa_pe0006_mercancias_prohibidas",         "url": BASE + "/legislacion/procedim/despacho/procAsociados/despa-pe.00.06.htm",                             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.00.06 - Mercancias Prohibidas y Restringidas"},
    {"nombre": "despa_pe0007_legajamiento",                  "url": BASE + "/legislacion/procedim/despacho/procAsociados/despa-pe.00.07.htm",                             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.00.07 - Legajamiento de Declaracion"},
    {"nombre": "despa_pe0011_rectificacion_electronica",     "url": BASE + "/legislacion/procedim/despacho/procAsociados/despa-pe.00.11.htm",                             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.00.11 - Rectificacion Electronica"},
    {"nombre": "despa_pe0012_medidas_frontera",              "url": BASE + "/legislacion/procedim/despacho/procAsociados/despa-pe.00.12.htm",                             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.00.12 - Medidas en Frontera"},
    {"nombre": "despa_pe0018_mandato_electronico",           "url": BASE + "/legislacion/procedim/despacho/procAsociados/despa-pe.00.18.htm",                             "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.00.18 - Mandato Electronico"},
    {"nombre": "despa_pe0101a_valoracion_omc",               "url": BASE + "/legislacion/procedim/despacho/importacion/importac/procEspecif/despa-pe-01-10a.htm",         "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.01.10a - Valoracion Mercancias segun OMC"},
    {"nombre": "despa_pe1301_envios_postales_especifico",    "url": BASE + "/legislacion/procedim/despacho/especiales/consecPostal/procEspecif/despa-pe-13-01.htm",              "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.13.01 - Envios Postales Especifico"},
    {"nombre": "despa_pe1801_rancho_nave",                   "url": BASE + "/legislacion/procedim/despacho/especiales/ranchoNave/procEspecif/despa-pe.18.01.htm",                "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.18.01 - Rancho de Nave"},
    {"nombre": "despa_it2501_mensajeria_instructivo",        "url": BASE + "/legislacion/procedim/despacho/especiales/mensajeria/instructivos/despa-it.25.01.htm",               "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-IT.25.01 - Mensajeria Internacional Instructivo"},
    {"nombre": "despa_pe0901_manifiesto_especifico_01",      "url": BASE + "/legislacion/procedim/despacho/manifiestos/procEspecif/despa-pe-09-01.htm",                          "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.09.01 - Manifiesto de Carga Especifico 01"},
    {"nombre": "despa_pe0902_manifiesto_especifico_02",      "url": BASE + "/legislacion/procedim/despacho/manifiestos/procEspecif/despa-pe-09-02.htm",                          "coleccion": "procedimientos_despacho",      "descripcion": "DESPA-PE.09.02 - Manifiesto de Carga Especifico 02"},

    # PROCEDIMIENTOS DE FISCALIZACION
    {"nombre": "control_pg01_programacion_ace",              "url": BASE + "/legislacion/procedim/fiscalizacion/procGeneral/control-pg.01.htm",                           "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PG.01 - Programacion de ACEs"},
    {"nombre": "control_pg02_ejecucion_ace",                 "url": BASE + "/legislacion/procedim/fiscalizacion/procGeneral/control-pg.02.htm",                           "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PG.02 - Ejecucion de ACEs"},
    {"nombre": "control_pe0001_inmovilizacion_incautacion",  "url": BASE + "/legislacion/procedim/pcontrab/procEspecif/control-pe.00.01.htm",                             "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.00.01 - Inmovilizacion e Incautacion"},
    {"nombre": "control_pe0008_precintos_aduaneros",         "url": BASE + "/legislacion/procedim/pcontrab/procEspecif/control-pe.00.08.htm",                             "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.00.08 - Precintos Aduaneros"},
    {"nombre": "control_pe0010_inspeccion_no_intrusiva",     "url": BASE + "/legislacion/procedim/pcontrab/procEspecif/control-pe.00.10.htm",                             "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.00.10 - Inspeccion No Intrusiva"},
    {"nombre": "control_pe0104_veedores",                    "url": BASE + "/legislacion/procedim/fiscalizacion/procEspecif/fisca-pe.01.04.htm",                          "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.01.04 - Veedores"},
    {"nombre": "control_pe0105_recepcion_denuncias",         "url": BASE + "/legislacion/procedim/fiscalizacion/procEspecif/fisca-pe.01.05.htm",                          "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.01.05 - Recepcion de Denuncias"},
    {"nombre": "control_pe0107_inspeccion_aerea",            "url": BASE + "/legislacion/procedim/pcontrab/procEspecif/control-pe.01.07.htm",                             "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.01.07 - Inspeccion Aduana Aerea"},
    {"nombre": "control_pe0109_fiscalizacion_posterior",     "url": BASE + "/legislacion/procedim/pcontrab/procEspecif/control-pe.01.09.htm",                             "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.01.09 - Fiscalizacion Posterior al Despacho"},
    {"nombre": "control_pe0110_fiscalizacion_operadores",    "url": BASE + "/legislacion/procedim/pcontrab/procEspecif/control-pe.01.10.htm",                             "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.01.10 - Fiscalizacion a Operadores"},
    {"nombre": "control_pe0202_material_radiactivo",         "url": BASE + "/legislacion/procedim/pcontrab/procEspecif/control-pe.02.02.htm",                             "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-PE.02.02 - Material Radiactivo"},
    {"nombre": "control_it0002_cierre_establecimientos",     "url": BASE + "/legislacion/procedim/pcontrab/instructivo/control-it.00.02.htm",                             "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-IT.00.02 - Cierre Establecimientos Ley 28008"},
    {"nombre": "control_it0001_inmovilizacion_instructivo",  "url": BASE + "/legislacion/procedim/pcontrab/instructivo/control-it.00.01.htm",                                    "coleccion": "procedimientos_fiscalizacion", "descripcion": "CONTROL-IT.00.01 - Instructivo Inmovilizacion"},

    # PROCEDIMIENTOS DE RECAUDACION
    {"nombre": "reca_pg02_control_ingresos",                 "url": BASE + "/legislacion/procedim/recauda/procGeneral/reca-pg.02.htm",                                    "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PG.02 - Control de Ingresos"},
    {"nombre": "reca_pg03_deuda_tributaria",                 "url": BASE + "/legislacion/procedim/recauda/procGeneral/reca-pg.03.htm",                                    "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PG.03 - Deuda Tributaria Aduanera"},
    {"nombre": "reca_pg04_reclamos_tributarios",             "url": BASE + "/legislacion/procedim/recauda/procGeneral/reca-pg.04.htm",                                    "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PG.04 - Reclamos Tributarios"},
    {"nombre": "reca_pg05_devoluciones_pagos",               "url": BASE + "/legislacion/procedim/recauda/procGeneral/reca-pg.05.htm",                                    "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PG.05 - Devoluciones de Pagos"},
    {"nombre": "reca_pe0201_extincion_deudas",               "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.02.01.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.02.01 - Extincion de Deudas por Pago"},
    {"nombre": "reca_pe0202_documentos_valorados",           "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.02.02.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.02.02 - Documentos Valorados"},
    {"nombre": "reca_pe0206_compensaciones",                 "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.02.06.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.02.06 - Compensaciones Ley 28625"},
    {"nombre": "reca_pe0302_reconocimiento_creditos",        "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.03.02.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.03.02 - Reconocimiento de Creditos"},
    {"nombre": "reca_pe0303_garantias_operativas",           "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.03.03.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.03.03 - Garantias Aduanas Operativas"},
    {"nombre": "reca_pe0304_garantias_operadores",           "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.03.04.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.03.04 - Garantias Operadores OCE"},
    {"nombre": "reca_pe0305_garantias_devolucion",           "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.03.05.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.03.05 - Devolucion Garantias OMC"},
    {"nombre": "reca_pe0306_garantias_previas",              "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.03.06.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.03.06 - Garantias Previas Numeracion"},
    {"nombre": "reca_pe0307_buenos_contribuyentes",          "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.03.07.htm",                                 "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.03.07 - Buenos Contribuyentes"},
{"nombre":    "reca_pe0203_notas_credito_debito",           "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.02.03.htm",                                        "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.02.03 - Notas de Credito y Debito"},
{"nombre": "reca_pe0205_aplazamiento_fraccionamiento",   "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.02.05.htm",                                        "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.02.05 - Aplazamiento y Fraccionamiento"},
{"nombre": "reca_pe0301_deuda_exigible_cobranza",        "url": BASE + "/legislacion/procedim/recauda/procEspecif/reca-pe.03.01.htm",                                        "coleccion": "procedimientos_recaudacion",   "descripcion": "RECA-PE.03.01 - Deuda Exigible en Cobranza Coactiva"},
]

# PDFs
PDFS = [
    {"nombre": "arancel_2022",                    "url": BASE + "/legislacion/procedim/normasadua/gja-04/ctrlCambios/anexos/Arancel_2022.pdf",    "coleccion": "arancel", "descripcion": "Arancel de Aduanas 2022"},
    {"nombre": "ds_163_2022_modificacion_arancel", "url": BASE + "/legislacion/procedim/normasadua/gja-04/ctrlCambios/anexos/DS_163-2022-EF.pdf", "coleccion": "arancel", "descripcion": "DS 163-2022-EF Modificacion Arancel"},
]

# ═══════════════════════════════════════════════════════════════
# SECCION 2: INDICES DE ESPECIFICOS E INSTRUCTIVOS (auto-discovery)
# ═══════════════════════════════════════════════════════════════
INDICES_ESPECIFICOS = [
    # DESPACHO
    BASE + "/legislacion/procedim/despacho/importacion/importac/procEspecif/index.htm",
    BASE + "/legislacion/procedim/despacho/importacion/importac/instructivos/index.htm",
    BASE + "/legislacion/procedim/despacho/exportacion/exportac/procEspecif/index.htm",
    BASE + "/legislacion/procedim/despacho/exportacion/exportac/instructivos/index.htm",
    BASE + "/legislacion/procedim/despacho/transito/transito/procEspecif/index.htm",
    BASE + "/legislacion/procedim/despacho/perfeccionam/drawback/procEspecif/index.htm",
    BASE + "/legislacion/procedim/despacho/deposito/deposito/procEspecif/index.htm",
    BASE + "/legislacion/procedim/despacho/especiales/mensajeria/procEspecif/index.htm",
    BASE + "/legislacion/procedim/despacho/especiales/envioEntRap/procEspecif/index.htm",
    BASE + "/legislacion/procedim/despacho/procAsociados/index.html",
    # FISCALIZACION
    BASE + "/legislacion/procedim/pcontrab/procEspecif/index.htm",
    BASE + "/legislacion/procedim/pcontrab/instructivos/index.htm",
    # RECAUDACION
    BASE + "/legislacion/procedim/recauda/procEspecif/index.htm",
]

# ═══════════════════════════════════════════════════════════════
# FUNCIONES
# ═══════════════════════════════════════════════════════════════
def explorar_indice(url_indice: str) -> list:
    """Extrae links de procedimientos no derogados de un indice."""
    try:
        resp = requests.get(url_indice, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        contenido = resp.content.decode("windows-1252")
        soup = BeautifulSoup(contenido, "lxml")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            texto = a.get_text().strip()
            # Saltar derogados
            if "derogad" in texto.lower() or "derogad" in href.lower():
                continue
            if not (href.endswith(".htm") or href.endswith(".html")):
                continue
            # Construir URL completa
            if href.startswith("http"):
                url = href
            elif href.startswith("/"):
                url = BASE + href
            else:
                base_dir = url_indice.rsplit("/", 1)[0]
                url = base_dir + "/" + href
            if "sunat.gob.pe" not in url:
                continue
            # Solo procedimientos especificos e instructivos
            patrones = ["despa-pe", "despa-it", "control-pe",
                        "control-it", "reca-pe", "reca-it"]
            if not any(p in url.lower() for p in patrones):
                continue
            nombre = url.split("/")[-1]
            nombre = re.sub(r'[.\-]', '_', nombre.lower()).replace("htm","").strip("_")
            links.append({
                "nombre": f"esp_{nombre}",
                "url": url,
                "coleccion": _asignar_coleccion_auto(url),
                "descripcion": texto[:80] or nombre
            })
        return links
    except Exception:
        return []

def _asignar_coleccion_auto(url: str) -> str:
    if "control" in url.lower():
        return "procedimientos_fiscalizacion"
    elif "reca" in url.lower():
        return "procedimientos_recaudacion"
    else:
        return "procedimientos_despacho"

def descargar_html(doc, i, total):
    destino = RAW_DIR / f"{doc['nombre']}.html"
    if destino.exists() and destino.stat().st_size > 5000:
        print(f"[{i:04d}/{total}] EXISTE  - {doc['nombre'][:55]}")
        return "existe"
    print(f"[{i:04d}/{total}] {doc['descripcion'][:60]}...")
    try:
        resp = requests.get(doc["url"], headers=headers, timeout=15)
        raw = resp.content

        # Intentar encodings en orden hasta encontrar el correcto
        contenido = None
        for enc in ["utf-8", "windows-1252", "latin-1"]:
            try:
                texto = raw.decode(enc, errors="strict")
                tiene_tildes = any(c in texto for c in "áéíóúñÁÉÍÓÚÑ")
                corruptos = texto.count("Ã±") + texto.count("ï¿½")
                if tiene_tildes and corruptos == 0:
                    contenido = texto
                    break
            except (UnicodeDecodeError, UnicodeEncodeError):
                continue

        # Si ninguno funciono usar windows-1252
        if contenido is None:
            contenido = raw.decode("windows-1252", errors="replace")

        if len(contenido) < 3000:
            print(f"         AVISO - muy pequeno ({len(contenido)} chars)")
            return "fallido"

        if "404" in contenido[:500] and "ERROR" in contenido[:500]:
            print(f"         AVISO - pagina 404")
            return "fallido"

        destino.write_text(contenido, encoding="utf-8")
        tiene_tildes = any(c in contenido for c in "áéíóúñÁÉÍÓÚÑ")
        estado = "OK" if tiene_tildes else "REVISAR"
        print(f"         {estado} - {len(contenido)/1024:.1f} KB | {doc['coleccion']}")
        time.sleep(0.3)
        return "ok"

    except Exception as e:
        print(f"         ERROR: {str(e)[:50]}")
        return "fallido"

def descargar_pdf(doc, i, total):
    destino = RAW_DIR / f"{doc['nombre']}.pdf"
    if destino.exists() and destino.stat().st_size > 10000:
        print(f"[{i:02d}/{total}] EXISTE  - {doc['nombre'][:55]}")
        return "existe"
    print(f"[{i:02d}/{total}] {doc['descripcion'][:60]}...")
    try:
        resp = requests.get(doc["url"], headers=headers, timeout=120, stream=True)
        total_bytes = 0
        with open(destino, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                total_bytes += len(chunk)
        print(f"         OK - {total_bytes/1024/1024:.1f} MB")
        return "ok"
    except Exception as e:
        print(f"         ERROR: {str(e)[:50]}")
        return "fallido"

# ═══════════════════════════════════════════════════════════════
# EJECUCION PRINCIPAL
# ═══════════════════════════════════════════════════════════════
print("=" * 65)
print("DESCARGA COMPLETA NORMATIVA SUNAT - ADUANA-GPT")
print("=" * 65)

# PASO 1: Explorar indices para descubrir especificos e instructivos
print("\nPASO 1: Explorando indices de procedimientos especificos...")
docs_descubiertos = []
urls_vistas = set(d["url"] for d in DOCUMENTOS_FIJOS)

for url_idx in INDICES_ESPECIFICOS:
    nombre_idx = url_idx.split("sunat.gob.pe")[-1]
    links = explorar_indice(url_idx)
    nuevos = 0
    for link in links:
        if link["url"] not in urls_vistas:
            urls_vistas.add(link["url"])
            docs_descubiertos.append(link)
            nuevos += 1
    if links or nuevos:
        print(f"  {nombre_idx[-60:]:60} -> {nuevos} nuevos")

print(f"\nDocumentos fijos:      {len(DOCUMENTOS_FIJOS)}")
print(f"Especificos descubiertos: {len(docs_descubiertos)}")
print(f"PDFs:                  {len(PDFS)}")
print(f"TOTAL:                 {len(DOCUMENTOS_FIJOS) + len(docs_descubiertos) + len(PDFS)}")

# PASO 2: Descargar todo
conteo = {"ok": 0, "existe": 0, "fallido": 0}
todos = DOCUMENTOS_FIJOS + docs_descubiertos
total = len(todos)

print(f"\nPASO 2: Descargando HTMLs ({total} documentos)...")
print("-" * 65)
for i, doc in enumerate(todos, 1):
    r = descargar_html(doc, i, total)
    conteo[r] += 1

print(f"\nPASO 3: Descargando PDFs ({len(PDFS)} archivos)...")
print("-" * 65)
for i, doc in enumerate(PDFS, 1):
    r = descargar_pdf(doc, i, len(PDFS))
    conteo[r] += 1

# RESUMEN
print()
print("=" * 65)
print("RESUMEN FINAL")
print("=" * 65)
colecciones = {}
for doc in todos + PDFS:
    col = doc["coleccion"]
    colecciones[col] = colecciones.get(col, 0) + 1
print("\nPor coleccion:")
for col, count in sorted(colecciones.items()):
    print(f"  {col:40} -> {count}")
print(f"\nNuevos descargados: {conteo['ok']}")
print(f"Ya existian:        {conteo['existe']}")
print(f"Fallidos:           {conteo['fallido']}")
print(f"\nTOTAL en data/raw:  {len(list(RAW_DIR.glob('*.*')))}")
print("\nDESCARGA COMPLETADA")