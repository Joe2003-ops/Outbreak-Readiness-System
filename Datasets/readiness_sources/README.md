# Kenya health-facility readiness sources

Downloaded on 2026-11-02 for the outbreak-readiness project. These are reports and survey documentation; they are not raw facility-level microdata.

## Files in this folder

- `Kenya_Health_Facility_Census_Report_September_2023.pdf` — Ministry of Health census report; indicators include facility amenities, IPC, workforce, services, equipment, infrastructure, laboratory readiness, medicines/tracers, beds, and emergency/referral capacity. Official source: https://www.health.go.ke/sites/default/files/2024-01/Kenya%20Health%20Facility%20Census%20Report%20September%202023.pdf
- `Kenya_QoC_HFA_2024_Service_Availability_Readiness_Report.pdf` — Ministry of Health 2024 quality-of-care HFA report on service availability/readiness. Official source: https://health.go.ke/sites/default/files/2026-06/Main%20Report%20-%20SARA%2021.10.2025.pdf
- `Kenya_QoC_HFA_2024_Quality_Systems_Human_Resources_Report.pdf` — 2024 quality systems / workforce report, hosted by Countdown 2030: https://countdown2030.org/wp-content/uploads/2025/10/Main-Report-HR-21.10.2025.pdf
- `Kenya_SDI_Health_Survey_2018_Report.pdf` — World Bank / Government of Kenya survey report: https://documents1.worldbank.org/curated/en/099430110062245298/pdf/IDU1b312d25b13d0a14c7f1b33c18786382b28ed.pdf
- `Kenya_SDI_Health_Survey_2018_Questionnaire_Masked.pdf` — masked survey questionnaire. Source: https://microdata.worldbank.org/catalog/3872/download/49943
- `Kenya_SDI_Health_Survey_2018_Field_Manual.pdf` — field manual. Source: https://microdata.worldbank.org/catalog/3872/download/49947
- `SDI_Health_Anonymization_Protocol.pdf` — public-use data anonymization documentation. Source: https://microdata.worldbank.org/catalog/3872/download/49945
- `SDI_Data_Harmonization_Protocol_February_2021.pdf` — harmonization documentation. Source: https://microdata.worldbank.org/catalog/3872/download/49946

## Raw survey data access

The best immediately usable facility-level candidate is the World Bank Kenya Service Delivery Indicators Health Survey 2018 public-use dataset: https://microdata.worldbank.org/index.php/catalog/3872

The catalog describes five Stata `.dta` files: facility module 1 (3,098 rows), provider absence module 2 (25,001 rows), clinical-vignette module 3 (4,499 rows), facility-finance module 4 (3,050 rows), and sampling weights (3,038 rows). The files are anonymized public-use microdata. On the download attempt, the catalog redirected to its login page, so the raw `.dta` files are not included here. Download them from the catalog after signing in and accepting its data-use terms. Do not use the public-use facility sample as a current census; the observations are from 2018 and survey weights/design must be considered.

The 2023 census and 2024 QoC-HFA reports are public, but I did not find facility-level raw data downloads on the official pages. For a current readiness model, request the anonymized facility-level data, codebook/questionnaires, sampling weights, and facility identifiers/geocodes from the Ministry of Health / KNBS.

## Citation

For the SDI microdata, cite Waly Wane, Jane Chuma, and the World Bank, *Service Delivery Indicators Health Survey 2018 - Harmonized Public Use Data*, reference `KEN_2018_SDI-H_v01_M_v01_A_PUF`, and record the date downloaded. Follow the use terms shown by the catalog.
