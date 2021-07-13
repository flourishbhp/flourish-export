caregiver_crfs_list = [
  'arvsprepregnancy',
  'caregiverclinicalmeasurementsFu',
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
  'caregiverpreviouslyenrolled',
  'foodsecurityquestionnaire',
  'hivdisclosurestatusa',
  'hivdisclosureStatusb',
  'hivdisclosureStatusc',
  'hivdisclosureStatusd',
  'hivrapidtestcounseling',
  'hivviralloadandcd4',
  'maternalarvduringpreg',
  'maternaldiagnoses',
  'maternalivInterimHx',
  'Maternalinterimidcc',
  'medicalhistory',
  'obstericalhistory',
  'sociodemographicdata',
  'substanceuseduringpregnancy',
  'substanceUsepriorpregnancy',
  'tbhistorypreg',
  'tbpresencehouseholdmembers',
  'tbscreenpreg',
  'ultrasound'
  ]

caregiver_inlines_dict = {
  'cliniciannotes': [['cliniciannotesimage'], 'clinician_notes_id'],
  'maternalarvduringpreg': [['maternalarv'], 'maternal_arv_durg_preg_id']
}

caregiver_model_list = [
  'antenatalEnrollment', 'caregiverchildconsent', 'caregiverlocator',
  'caregiverpreviouslyenrolled', 'flourishconsentversion',
  'inpersoncontactAttempt', 'maternaldelivery', 'maternalarv'
]

caregiver_many_to_many_crf = [
  ['arvsprepregnancy', 'prior_arv', 'priorarv'],
  ['maternaldiagnoses', 'who', 'wcsdxadult'],
  ['medicalhistory', 'caregiver_chronic', 'chronicConditions',],
  ['medicalhistory', 'who', 'wcsdxadult',]
  ['medicalhistory', 'caregiver_medications', 'caregiverMedications',]
]

caregiver_many_to_many_non_crf = [[
    'maternaldelivery','delivery_complications',],]

offstudy_prn_model_list = ['caregiveroffstudy','childoffstudy',]

death_report_prn_model_list = ['deathReport',]

child_crf_list = [
  'academicperformance',
  'birthdata',
  'birthexam',
  'birthfeedingvaccine',
  'childbirthscreening',
  'childclinicalmeasurements',
  'childcliniciannotes',
  'childfoodSecurityquestionnaire',
  'childgadAnxietyscreening',
  'childgadreferral',
  'childhivrapidTestcounseling',
  'childimmunizationhistory',
  'childmedicalhistory',
  'childphqDepressionscreening',
  'childphqReferral',
  'childphysicalactivity',
  'childpregtesting',
  'childprevioushospitalization',
  'childsociodemographic',
  'childtannerstaging',
  'childworkingstatus',
  'infantarvexposure',
  'infantcongenitalanomalies',
  'infantfeeding',
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
    'infanttrisomies',], 'congenital_anomalies_id'],
  'birthfeedingvaccine': [['birthvaccines'], 'birth_feed_vaccine_id'],
  'childcliniciannotes': [['cliniciannotesImage'], 'clinician_notes_id'],
  'childimmunizationhistory': [['vaccinesmissed', 'vaccinesreceived'],
                               'child_immunization_history_id'],  
  'infantcongenitalanomalies': [[
      'infantcns', 'infantfacialdefect', 'infantcleftdisorder',
      'infantmouthupgi', 'infantmouthupgi', 'infantcardiodisorder',
      'infantrespiratoryDefect', 'infantlowergi', 'infantfemalegenital',
      'infantmalegenital', 'infantrenal', 'infantmusculoskeletal', 'infantskin',
      'infanttrisomies'], 'congenital_anomalies_id']}

child_many_to_many_crf = [
  ['childmedicalhistory', 'child_chronic', 'childdiseases'],
  ['childPrevioushospitalization', 'reason_hospitalized','childdiseases'],
]

child_model_list = [
    'childassent', 'appointment', 'childcontinuedconsent', 'childdataset',
    'childdummysubjectconsent', 'childprehospitalizationinline', 'childvisit']
