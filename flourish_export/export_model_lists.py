exclude_fields = [
    'created', '_state', 'hostname_created', 'hostname_modified', 'revision',
    'device_created', 'device_modified', 'id', 'site_id', 'created_time',
    'modified_time', 'report_datetime_time', 'registration_datetime_time',
    'screening_datetime_time', 'modified', 'form_as_json', 'consent_model',
    'randomization_datetime', 'registration_datetime', 'is_verified_datetime',
    'first_name', 'last_name', 'initials', 'guardian_name', 'identity',
    'infant_visit_id', 'maternal_visit_id', 'processed', 'processed_datetime',
    'packed', 'packed_datetime', 'shipped', 'shipped_datetime',
    'received_datetime', 'identifier_prefix', 'primary_aliquot_identifier',
    'clinic_verified', 'clinic_verified_datetime', 'drawn_datetime',
    'related_tracking_identifier', 'parent_tracking_identifier']

exclude_m2m_fields = exclude_fields + ['display_index', 'field_name',
                                       'name', 'version']

caregiver_crfs_list = [
  'arvsprepregnancy',
  'caregiverclinicalmeasurementsfu',
  'caregiverclinicalmeasurements',
  'cliniciannotes',
  'caregiveredinburghdeprscreening',
  'caregiveredinburghreferral',
  'caregivergadanxietyscreening',
  'caregivergadreferral',
  'caregiverhamddeprscreening',
  'caregiverhamdreferral',
  'caregiverphqdeprscreening',
  'caregiverphqreferral',
  'covid19',
  'foodsecurityquestionnaire',
  'hivdisclosurestatusa',
  'hivdisclosurestatusb',
  'hivdisclosurestatusc',
  'hivrapidtestcounseling',
  'hivviralloadandcd4',
  'maternalarvduringpreg',
  'maternaldiagnoses',
  'maternalhivinterimhx',
  'Maternalinterimidcc',
  'medicalhistory',
  'obstericalhistory',
  'sociodemographicdata',
  'substanceuseduringpregnancy',
  'substanceusepriorpregnancy',
  'tbhistorypreg',
  'tbpresencehouseholdmembers',
  'tbroutinehealthscreen',
  'tbscreenpreg',
  'ultrasound'
  ]

caregiver_inlines_dict = {
  'cliniciannotes': [['cliniciannotesimage'], 'clinician_notes_id'],
  'maternalarvduringpreg': [['maternalarv'], 'maternal_arv_durg_preg_id'],
}

caregiver_model_list = [
  'antenatalenrollment', 'subjectconsent', 'caregiverchildconsent',
  'caregiverpreviouslyenrolled', 'flourishconsentversion',
  'maternaldelivery', 'caregiverpreviouslyenrolled', 'caregivercontact',
  'caregiverlocator'
]

caregiver_many_to_many_crf = [
  ['arvsprepregnancy', 'prior_arv', 'priorarv'],
  ['maternaldiagnoses', 'who', 'wcsdxadult'],
  ['medicalhistory', 'caregiver_chronic', 'chronicconditions', ],
  ['medicalhistory', 'who', 'wcsdxadult', ],
  ['medicalhistory', 'caregiver_medications', 'caregivermedications', ],
  ['covid19', 'isolations_symptoms', 'covidsymptoms', ],
  ['covid19', 'symptoms_for_past_14days', 'covidsymptomsafter14days']
]

caregiver_many_to_many_non_crf = [[
    'maternaldelivery', 'delivery_complications', ], ]

offstudy_prn_model_list = ['caregiveroffstudy', 'childoffstudy', ]

death_report_prn_model_list = ['caregiverdeathreport', 'childdeathreport', ]

follow_model_list = ['booking', 'logentry', 'inpersonlog',
                     'inpersoncontactattempt', 'worklist']

follow_model_inlines_dict = {
    'inpersonlog': [['inpersoncontactattempt'], 'in_person_log_id']}

follow_model_many_to_many = [
    ['logentry', 'appt_reason_unwilling', 'reasonsunwilling']]

child_crf_list = [
  'academicperformance',
  'birthdata',
  'birthexam',
  'birthfeedingvaccine',
  'childbirthscreening',
  'childclinicalmeasurements',
  'childcliniciannotes',
  'childfoodsecurityquestionnaire',
  'childgadanxietyscreening',
  'childgadreferral',
  'childhivrapidtestcounseling',
  'childimmunizationhistory',
  'childmedicalhistory',
  'childphqdepressionscreening',
  'childphqreferral',
  'childphysicalactivity',
  'childpregtesting',
  'childprevioushospitalization',
  'childsociodemographic',
  'childtannerstaging',
  'childworkingstatus',
  'infantarvexposure',
  'infantcongenitalanomalies',
  'infantfeedingpractices',
  'infantfeeding',
  'childcovid19'
  ]

child_inlines_dict = {
  'infantcongenitalanomalies': [[
    'infantcns',
    'infantfacialdefect',
    'infantcleftdisorder',
    'infantmouthupgi',
    'infantcardiodisorder',
    'infantrespiratorydefect',
    'infantlowergi',
    'infantfemalegenital',
    'infantmalegenital',
    'infantrenal',
    'infantmusculoskeletal',
    'infantskin',
    'infanttrisomies', ], 'congenital_anomalies_id'],
  'birthfeedingvaccine': [['birthvaccines'], 'birth_feed_vaccine_id'],
  'childcliniciannotes': [['cliniciannotesimage'], 'clinician_notes_id'],
  'childimmunizationhistory': [['vaccinesmissed', 'vaccinesreceived'],
                               'child_immunization_history_id'],
  'infantcongenitalanomalies': [[
      'infantcns', 'infantfacialdefect', 'infantcleftdisorder',
      'infantmouthupgi', 'infantmouthupgi', 'infantcardiodisorder',
      'infantrespiratoryDefect', 'infantlowergi', 'infantfemalegenital',
      'infantmalegenital', 'infantrenal', 'infantmusculoskeletal', 'infantskin',
      'infanttrisomies'], 'congenital_anomalies_id'],
  'childprevioushospitalization': [['childprehospitalizationinline'], 'child_pre_hospitalization_id']}

child_many_to_many_crf = [
  ['childmedicalhistory', 'child_chronic', 'childdiseases'],
  ['childprevioushospitalization', 'reason_hospitalized', 'childdiseases'],
  ['childcovid19', 'isolations_symptoms', 'childcovidsymptoms'],
  ['childcovid19', 'symptoms_for_past_14days', 'childcovidsymptomsafter14days'],
  ['infantfeeding', 'solid_foods', 'solidfoods']
]

child_model_list = [
    'childassent', 'appointment', 'childcontinuedconsent', 'childdataset',
    'childdummysubjectconsent', 'childprehospitalizationinline', 'childvisit']
