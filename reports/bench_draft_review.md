# KautilyaBench v1 - draft review

Edit `data/bench/draft.jsonl` directly (it is the source of truth).
Delete bad rows entirely; fix query wording or gold ids where needed.

## regime_old (21)

- `kb001` punishment for murder | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s302
- `kb003` attempt to murder punishment | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s307
- `kb005` cheating and dishonestly inducing delivery of property | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s420
- `kb007` dowry death punishment | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s304B
- `kb009` husband subjecting wife to cruelty | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s498A
- `kb011` culpable homicide not amounting to murder | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s304
- `kb013` punishment for theft | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s379
- `kb015` robbery and dacoity punishment | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s392
- `kb017` criminal conspiracy | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s120B
- `kb019` outraging modesty of a woman | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s354
- `kb021` kidnapping for ransom | date=2024-03-15 | regimes={'criminal': 'old'}
  - gold: IPC_s364A
- `kb023` registration of FIR information in cognizable offences | date=2024-03-15 | regimes={'criminal_procedure': 'old'}
  - gold: CRPC_s154
- `kb025` regular bail in non-bailable offence | date=2024-03-15 | regimes={'criminal_procedure': 'old'}
  - gold: CRPC_s437_p0, CRPC_s437_p1
- `kb027` anticipatory bail | date=2024-03-15 | regimes={'criminal_procedure': 'old'}
  - gold: CRPC_s438_p0, CRPC_s438_p1
- `kb029` police to produce arrested person before magistrate within 24 hours | date=2024-03-15 | regimes={'criminal_procedure': 'old'}
  - gold: CRPC_s57
- `kb031` right of accused against self incrimination free legal aid | date=2024-03-15 | regimes={'criminal_procedure': 'old'}
  - gold: CRPC_s304
- `kb033` charge sheet completion timeline investigation custody | date=2024-03-15 | regimes={'criminal_procedure': 'old'}
  - gold: CRPC_s167_p0, CRPC_s167_p1, CRPC_s167_p2, CRPC_s167_p3 ...
- `kb035` maintenance of wife children and parents | date=2024-03-15 | regimes={'criminal_procedure': 'old'}
  - gold: CRPC_s125_p0, CRPC_s125_p1
- `kb037` admissibility of electronic records certificate | date=2024-03-15 | regimes={'evidence': 'old'}
  - gold: IEA_s65B
- `kb039` opinions of experts admissibility | date=2024-03-15 | regimes={'evidence': 'old'}
  - gold: IEA_s45
- `kb041` statement of relevant fact by person who is dead or cannot attend | date=2024-03-15 | regimes={'evidence': 'old'}
  - gold: IEA_s32

## regime_new (21)

- `kb002` punishment for murder (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s103
- `kb004` attempt to murder punishment (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s109
- `kb006` cheating and dishonestly inducing delivery of property (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s318
- `kb008` dowry death punishment (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s80
- `kb010` husband subjecting wife to cruelty (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s85, BNS_s86
- `kb012` culpable homicide not amounting to murder (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s105
- `kb014` punishment for theft (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s303
- `kb016` robbery and dacoity punishment (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s309
- `kb018` criminal conspiracy (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s61
- `kb020` outraging modesty of a woman (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s74
- `kb022` kidnapping for ransom (incident happened in September 2024) | date=2024-09-15 | regimes={'criminal': 'new'}
  - gold: BNS_s140
- `kb024` registration of FIR information in cognizable offences (offence dated June 2025) | date=2025-06-01 | regimes={'criminal_procedure': 'new'}
  - gold: BNSS_s173
- `kb026` regular bail in non-bailable offence (offence dated June 2025) | date=2025-06-01 | regimes={'criminal_procedure': 'new'}
  - gold: BNSS_s480_p0, BNSS_s480_p1
- `kb028` anticipatory bail (offence dated June 2025) | date=2025-06-01 | regimes={'criminal_procedure': 'new'}
  - gold: BNSS_s482
- `kb030` police to produce arrested person before magistrate within 24 hours (offence dated June 2025) | date=2025-06-01 | regimes={'criminal_procedure': 'new'}
  - gold: BNSS_s58
- `kb032` right of accused against self incrimination free legal aid (offence dated June 2025) | date=2025-06-01 | regimes={'criminal_procedure': 'new'}
  - gold: BNSS_s341
- `kb034` charge sheet completion timeline investigation custody (offence dated June 2025) | date=2025-06-01 | regimes={'criminal_procedure': 'new'}
  - gold: BNSS_s187_p0, BNSS_s187_p1
- `kb036` maintenance of wife children and parents (offence dated June 2025) | date=2025-06-01 | regimes={'criminal_procedure': 'new'}
  - gold: BNSS_s144
- `kb038` admissibility of electronic records certificate (trial for a 2025 offence) | date=2025-02-10 | regimes={'evidence': 'new'}
  - gold: BSA_s63_p0, BSA_s63_p1
- `kb040` opinions of experts admissibility (trial for a 2025 offence) | date=2025-02-10 | regimes={'evidence': 'new'}
  - gold: BSA_s39
- `kb042` statement of relevant fact by person who is dead or cannot attend (trial for a 2025 offence) | date=2025-02-10 | regimes={'evidence': 'new'}
  - gold: BSA_s26

## landmark (18)

- `kb043` basic structure doctrine Kesavananda Bharati
  - gold: SCJ_S_1973_1_1_1002_IN THE SUPRE, SCJ_S_1973_1_1_1002_ORDER, SCJ_S_1973_1_1_1002_PREAMBLE_p0, SCJ_S_1973_1_1_1002_PREAMBLE_p1 ...
- `kb044` right to privacy fundamental right Puttaswamy
  - gold: SCJ_2017_10_569_999_ORDER OF THE, SCJ_2017_10_569_999_PREAMBLE_p0, SCJ_2017_10_569_999_PREAMBLE_p1, SCJ_2017_10_569_999_PREAMBLE_p10 ...
- `kb045` President's rule state emergency Bommai safeguards
  - gold: SCJ_1994_2_644_1000_MADHYA PRADE, SCJ_1994_2_644_1000_ROLE OF THE , SCJ_1994_2_644_1000_RENOTIFICTJO, SCJ_1994_2_644_1000_PREAMBLE_p0 ...
- `kb046` death penalty rarest of rare Bachan Singh
  - gold: SCJ_1983_1_145_371_PREAMBLE_p0, SCJ_1983_1_145_371_PREAMBLE_p1, SCJ_1983_1_145_371_PREAMBLE_p10, SCJ_1983_1_145_371_PREAMBLE_p100 ...
- `kb047` rarest of rare case guidelines Machhi Singh
  - gold: SCJ_1983_3_413_437_PREAMBLE_p0, SCJ_1983_3_413_437_PREAMBLE_p1, SCJ_1983_3_413_437_PREAMBLE_p10, SCJ_1983_3_413_437_PREAMBLE_p11 ...
- `kb048` section 303 mandatory death sentence unconstitutional Mithu
  - gold: SCJ_1983_2_690_713_PREAMBLE_p0, SCJ_1983_2_690_713_PREAMBLE_p1, SCJ_1983_2_690_713_PREAMBLE_p2, SCJ_1983_2_690_713_PREAMBLE_p3 ...
- `kb049` certificate under section 65B mandatory Anvar Basheer
  - gold: SCJ_2014_11_399_427_PREAMBLE_p0, SCJ_2014_11_399_427_PREAMBLE_p1, SCJ_2014_11_399_427_PREAMBLE_p10, SCJ_2014_11_399_427_PREAMBLE_p11 ...
- `kb050` 65B certificate overruled Arjun Panditrao Khotkar position
  - gold: SCJ_2020_7_180_282_PREAMBLE_p0, SCJ_2020_7_180_282_PREAMBLE_p1, SCJ_2020_7_180_282_PREAMBLE_p10, SCJ_2020_7_180_282_PREAMBLE_p11 ...
- `kb051` zero FIR mandatory registration Lalita Kumari
  - gold: SCJ_2013_14_713_802_PREAMBLE_p0, SCJ_2013_14_713_802_PREAMBLE_p1, SCJ_2013_14_713_802_PREAMBLE_p10, SCJ_2013_14_713_802_PREAMBLE_p11 ...
- `kb052` arrest guidelines Arnesh Kumar 41A notice
  - gold: SCJ_2014_8_128_143_PREAMBLE_p0, SCJ_2014_8_128_143_PREAMBLE_p1, SCJ_2014_8_128_143_PREAMBLE_p2, SCJ_2014_8_128_143_PREAMBLE_p3 ...
- `kb053` arrest safeguards D.K. Basu memo grounds
  - gold: SCJ_S_1996_10_284_320_PREAMBLE_p0, SCJ_S_1996_10_284_320_PREAMBLE_p1, SCJ_S_1996_10_284_320_PREAMBLE_p10, SCJ_S_1996_10_284_320_PREAMBLE_p11 ...
- `kb054` reading down section 377 decriminalisation Navtej Johar
  - gold: SCJ_2018_7_379_746_PREAMBLE, SCJ_2018_7_379_746_MINISTRY OF _p0, SCJ_2018_7_379_746_MINISTRY OF _p1, SCJ_2018_7_379_746_MINISTRY OF _p10 ...
- `kb055` online speech 66A struck down Shreya Singhal
  - gold: SCJ_2015_5_963_1074_PREAMBLE_p0, SCJ_2015_5_963_1074_PREAMBLE_p1, SCJ_2015_5_963_1074_PREAMBLE_p10, SCJ_2015_5_963_1074_PREAMBLE_p11 ...
- `kb056` narco analysis test self incrimination Selvi
  - gold: SCJ_2010_5_381_594_CONCLUSION, SCJ_2010_5_381_594_PREAMBLE_p0, SCJ_2010_5_381_594_PREAMBLE_p1, SCJ_2010_5_381_594_PREAMBLE_p10 ...
- `kb057` living will euthanasia Common Cause
  - gold: SCJ_2018_6_1_386_PREAMBLE_p0, SCJ_2018_6_1_386_PREAMBLE_p1, SCJ_2018_6_1_386_PREAMBLE_p10, SCJ_2018_6_1_386_PREAMBLE_p100 ...
- `kb058` doctrine of harmonious construction Golak Nath
  - gold: SCJ_1967_2_762_948_PREAMBLE_p0, SCJ_1967_2_762_948_PREAMBLE_p1, SCJ_1967_2_762_948_PREAMBLE_p10, SCJ_1967_2_762_948_PREAMBLE_p100 ...
- `kb059` pavement dwellers right to livelihood Olga Tellis
  - gold: SCJ_S_1985_2_51_99_PREAMBLE_p0, SCJ_S_1985_2_51_99_PREAMBLE_p1, SCJ_S_1985_2_51_99_PREAMBLE_p10, SCJ_S_1985_2_51_99_PREAMBLE_p11 ...
- `kb060` visceral hatred speech incitement Tehseen Poonawalla lynching
  - gold: SCJ_2018_9_291_328_PREAMBLE_p0, SCJ_2018_9_291_328_PREAMBLE_p1, SCJ_2018_9_291_328_PREAMBLE_p10, SCJ_2018_9_291_328_PREAMBLE_p11 ...

## labour (5)

- `kb061` gratuity eligibility payment and amount determination | regimes={'labour': 'current'}
  - gold: SSCODE_s53_p0, SSCODE_s53_p1, SSCODE_s53_p0, SSCODE_s53_p1
- `kb062` maternity benefit leave duration | regimes={'labour': 'current'}
  - gold: SSCODE_s60, SSCODE_s62
- `kb063` retrenchment compensation and notice period for workmen | regimes={'labour': 'current'}
  - gold: IRCODE_s70, IRCODE_s71
- `kb064` provident fund contribution employer employee | regimes={'labour': 'current'}
  - gold: IRCODE_s15, IRCODE_s83
- `kb065` factory safety committee duties occupier | regimes={'labour': 'current'}
  - gold: OSHCODE_s5, OSHCODE_s16

## tax (4)

- `kb066` long term capital gains transfer of shares (for FY 2025) | date=2025-08-01 | regimes={'tax': 'old'}
  - gold: ITA1961_s46A, ITA1961_s111A
- `kb067` income tax refund procedure delay (for FY 2026) | date=2026-05-20 | regimes={'tax': 'new'}
  - gold: ITA2025_s426, ITA2025_s431
- `kb068` assessment of escaped income best judgement assessment (for FY 2025) | date=2025-12-01 | regimes={'tax': 'old'}
  - gold: ITA1961_s147_p0, ITA1961_s147_p1, ITA1961_s147_p0, ITA1961_s147_p1
- `kb069` annual value of house property let out (for FY 2026) | date=2026-06-15 | regimes={'tax': 'new'}
  - gold: ITA2025_s20, ITA2025_s22

## ask_date (4)

- `kb070` what was the law on cheating when my uncle was duped back then? [ASK-DATE]
  - gold: IPC_s420
- `kb071` which section applied to dowry cases earlier? [ASK-DATE]
  - gold: IPC_s420
- `kb072` bail provisions that used to apply at that time [ASK-DATE]
  - gold: IPC_s420
- `kb073` what did the evidence act say about electronic records before? [ASK-DATE]
  - gold: IPC_s420

## hindi (8)

- `kb074` hatya ki saza kya hai March 2023 mein hua tha [hi] | date=2023-03-01 | regimes={'criminal_substantive': 'old'}
  - gold: IPC_s302
- `kb075` March 2024 mein mere saath dhokha hua tha kaunsa section lagega [hi] | date=2024-03-01 | regimes={'criminal_substantive': 'old'}
  - gold: IPC_s415, IPC_s420
- `kb076` june 2025 mein cheating hui thi kaunsa kanoon lagega [hi] | date=2025-06-01 | regimes={'criminal_substantive': 'new'}
  - gold: BNS_s318
- `kb077` electronic evidence ka certificate zaroori hai kya [hi]
  - gold: IEA_s65B
- `kb078` gratuity kitne saal baad milta hai [hi]
  - gold: SSCODE_s53_p0, SSCODE_s53_p1
- `kb079` fir darj karne ka niyam kya tha pehle [hi]
  - gold: CRPC_s154
- `kb080` girftari ke baad kitne ghante mein court jana chahiye [hi]
  - gold: CRPC_s57
- `kb081` anticipatory bail kya hai aur kab milti hai [hi]
  - gold: CRPC_s438_p0, CRPC_s438_p1

## gap (4)

- `kb082` how do I register a private limited company? [MUST-REFUSE]
  - gold: IPC_s420
- `kb083` compensation claim under the Motor Vehicles Act for accidents [MUST-REFUSE]
  - gold: IPC_s420
- `kb084` US visa application process for Indian citizens [MUST-REFUSE]
  - gold: IPC_s420
- `kb085` divorce procedure under Hindu Marriage Act [MUST-REFUSE]
  - gold: IPC_s420

## auto_lookup (30)

- `kb086` what does section 69 of Indian Penal Code cover?
  - gold: IPC_s69
- `kb087` what does section 76 of Indian Penal Code cover?
  - gold: IPC_s76
- `kb088` what does section 336 of Indian Penal Code cover?
  - gold: IPC_s336
- `kb089` what does section 225 of Indian Penal Code cover?
  - gold: IPC_s225
- `kb090` what does section 257 of Bharatiya Nyaya Sanhita cover?
  - gold: BNS_s257
- `kb091` what does section 144 of Bharatiya Nyaya Sanhita cover?
  - gold: BNS_s144
- `kb092` what does section 41 of Bharatiya Nyaya Sanhita cover?
  - gold: BNS_s41
- `kb093` what does section 35 of Bharatiya Nyaya Sanhita cover?
  - gold: BNS_s35
- `kb094` what does section 469 of Code of Criminal Procedure cover?
  - gold: CRPC_s469
- `kb095` what does section 380 of Code of Criminal Procedure cover?
  - gold: CRPC_s380
- `kb096` what does section 105E of Code of Criminal Procedure cover?
  - gold: CRPC_s105E
- `kb097` what does section 485 of Bharatiya Nagarik Suraksha Sanhita cover?
  - gold: BNSS_s485
- `kb098` what does section 531 of Bharatiya Nagarik Suraksha Sanhita cover?
  - gold: BNSS_s531_p0, BNSS_s531_p1, BNSS_s531_p10, BNSS_s531_p11 ...
- `kb099` what does section 2 of Bharatiya Nagarik Suraksha Sanhita cover?
  - gold: BNSS_s2_p0, BNSS_s2_p1, BNSS_s2_p10, BNSS_s2_p11 ...
- `kb100` what does section 159 of Indian Evidence Act cover?
  - gold: IEA_s159
- `kb101` what does section 135 of Indian Evidence Act cover?
  - gold: IEA_s135
- `kb102` what does section 39 of Bharatiya Sakshya Adhiniyam cover?
  - gold: BSA_s39
- `kb103` what does section 1 of Bharatiya Sakshya Adhiniyam cover?
  - gold: BSA_s1
- `kb104` what does section 12 of Income-tax Act cover?
  - gold: ITA1961_s12_p0, ITA1961_s12_p1, ITA1961_s12_p10, ITA1961_s12_p11 ...
- `kb105` what does section 18 of Income-tax Act cover?
  - gold: ITA1961_s18
- `kb106` what does section 271G of Income-tax Act cover?
  - gold: ITA1961_s271G
- `kb107` what does section 23 of Income-tax Act cover?
  - gold: ITA2025_s23
- `kb108` what does section 131 of Income-tax Act cover?
  - gold: ITA2025_s131
- `kb109` what does section 500 of Income-tax Act cover?
  - gold: ITA2025_s500
- `kb110` what does section 81 of Constitution of India cover?
  - gold: COI_s81
- `kb111` what does section 239A of Constitution of India cover?
  - gold: COI_s239A
- `kb112` what does section 56 of Industrial Relations Code cover?
  - gold: IRCODE_s56
- `kb113` what does section 111 of Occupational Safety cover?
  - gold: OSHCODE_s111
- `kb114` what does section 34 of Code on Social Security cover?
  - gold: SSCODE_s34
- `kb115` what does section 59 of Code on Wages cover?
  - gold: WAGECODE_s59
