# Data Quality Notes — NYC 311 Dataset
**Dataset:** 311 Service Requests from 2020 to Present  
**Source:** https://data.cityofnewyork.us/resource/erm2-nwe9  
**Subset:** 500,000 rows extracted via Socrata API  
**Final clean row count:** 494,063  

---

## 1. NULL Latitude / Longitude

**Finding:**
- 11,442 rows have NULL latitude and longitude
- Percentage: **2.32%** (expected ~15% — actual data is cleaner than anticipated)
- Both columns always null together — never one without the other

**Issues found:**
- Latitude/longitude stored as strings in raw JSON, not floats
- Missing values present as empty strings and NaN

**Cleaning applied:**
- Cast both columns to `float` using `pd.to_numeric(errors='coerce')`
- Invalid or empty values automatically became `NaN` → `NULL` in PostgreSQL

**Decision:**
- Both columns marked as **nullable** in PostgreSQL schema
- Pydantic model uses `Optional[float] = None`

---

## 2. Borough Unique Values

**Finding (raw data — before cleaning):**
```
BROOKLYN         ~150,000
QUEENS           ~120,000
MANHATTAN        ~100,000
BRONX             ~80,000
STATEN ISLAND     ~40,000
Unspecified        ~8,000   ← invalid
NaN                ~2,000   ← missing
```
Total unique values in raw data: **6 (including Unspecified)**

**Issues found:**
- `'Unspecified'` is not a valid NYC borough
- Inconsistent casing across rows: `'brooklyn'`, `'Brooklyn'`, `'BROOKLYN'`
- Some rows had no borough value at all (NaN)

**Cleaning applied:**
1. Replaced `'Unspecified'` → `NaN`
2. Replaced empty strings → `NaN`
3. Normalized all valid values to UPPERCASE via `.str.upper().str.strip()`
4. Dropped all rows where borough is `NaN` → **5,937 rows removed**

**After cleaning — 5 valid values only:**
```
BROOKLYN
QUEENS
MANHATTAN
BRONX
STATEN ISLAND
```

**Decision:**
- Borough marked as **NOT NULL** in PostgreSQL
- Pydantic uses a strict `Enum` with exactly 5 valid values
- Invalid borough on API request → rejected with 422 error

---

## 3. Invalid ZIP Codes

**Finding (raw data):**
```
NaN / empty    → 8,924 rows (1.81%)
'N/A'          → 0 rows ✅
'00000'        → 0 rows ✅
''             → 0 rows ✅
' '            → 0 rows ✅
```

**Issues found:**
- ZIP stored as `float64` by pandas (e.g. `10001.0`) because NaN forced float conversion
- No garbage string values found — data was cleaner than expected

**Cleaning applied:**
- Converted float ZIP back to clean 5-digit string using `str(int(x)).zfill(5)`
- Any value not matching `^\d{5}$` → replaced with `None`
- Final dtype: `object` (string) ✅

**Verification result:**
```
'00000': 0 rows  ✅
'N/A':   0 rows  ✅
'':      0 rows  ✅
' ':     0 rows  ✅
```
All invalid ZIP values confirmed clean after coercion step.

**Decision:**
- `incident_zip` is **nullable** in PostgreSQL as `VARCHAR(10)`
- Only remaining nulls are the 8,924 rows with no ZIP recorded
- Pydantic validator uses regex `^\d{5}$` to validate ZIP on API input
- Invalid ZIP on incoming request → rejected with 422 error

---

## 4. Date Range of created_date

**Finding:**
```
Earliest:   2020-01-01
Latest:     2024-12-31
Range:      ~5 years of complaint data
```

**Issues found:**
- All date columns stored as raw strings in JSON — required casting
- `closed_date` NULL for all open/pending complaints — expected behavior
- `resolution_action_updated_date` NULL when no resolution action taken yet

**Cleaning applied:**
- All date columns cast using `pd.to_datetime(errors='coerce')`
- Final dtype: `datetime64[us]` ✅
- `NaT` values automatically convert to `NULL` in PostgreSQL

**Decision:**
- `created_date` is **NOT NULL** in PostgreSQL — every complaint must have one
- `closed_date` and `resolution_action_updated_date` are **nullable**
- Pydantic uses `datetime` for `created_date`, `Optional[datetime]` for others
- API date filters will validate `start_date` is not after `end_date`

---

## 5. Actual Null Counts (Post Cleaning)

**Total rows: 494,063**

| Column | Null Count | Percentage | Nullable in DB |
|---|---|---|---|
| `unique_key` | 0 | 0.00% | NO |
| `created_date` | 0 | 0.00% | NO |
| `closed_date` | 4,872 | 0.99% | YES |
| `agency` | 0 | 0.00% | NO |
| `agency_name` | 0 | 0.00% | NO |
| `complaint_type` | 0 | 0.00% | NO |
| `descriptor` | 7,009 | 1.42% | YES |
| `location_type` | 132,541 | 26.83% | YES |
| `incident_zip` | 8,924 | 1.81% | YES |
| `city` | 26,356 | 5.33% | YES |
| `borough` | 0 | 0.00% | NO |
| `status` | 0 | 0.00% | NO |
| `resolution_description` | 50,161 | 10.15% | YES |
| `latitude` | 11,442 | 2.32% | YES |
| `longitude` | 11,442 | 2.32% | YES |
| `resolution_action_updated_date` | 3,047 | 0.62% | YES |

---

## 6. Final Dtype Verification

All columns confirmed correct after cleaning:

```
unique_key                          int64
created_date                datetime64[us]
closed_date                 datetime64[us]
agency                               str
agency_name                          str
complaint_type                       str
descriptor                           str
location_type                        str
incident_zip                         str
city                                 str
borough                              str
status                               str
resolution_description               str
latitude                         float64
longitude                        float64
resolution_action_updated_date  datetime64[us]
```

---

## 7. Pydantic Model Decisions

| Column | Pydantic Type |
|---|---|
| `unique_key` | `int` |
| `created_date` | `datetime` |
| `closed_date` | `Optional[datetime]` |
| `agency` | `str` |
| `agency_name` | `str` |
| `complaint_type` | `str` |
| `descriptor` | `Optional[str]` |
| `location_type` | `Optional[str]` |
| `incident_zip` | `Optional[str]` — regex `^\d{5}$` |
| `city` | `Optional[str]` |
| `borough` | `Enum` (BROOKLYN, QUEENS, MANHATTAN, BRONX, STATEN ISLAND) |
| `status` | `str` |
| `resolution_description` | `Optional[str]` |
| `latitude` | `Optional[float]` |
| `longitude` | `Optional[float]` |
| `resolution_action_updated_date` | `Optional[datetime]` |

---

## 8. Rows Removed During Cleaning

| Reason | Rows Removed |
|---|---|
| NULL or Unspecified borough | 5,937 |
| **Final clean row count** | **494,063** |

---

## 9. Key Observations

- `location_type` has the highest null rate at **26.83%** — 1 in 4 rows — too high to drop, kept as nullable
- `latitude` null rate was **2.32%** — significantly lower than the expected ~15%
- All 7 non-nullable columns confirmed **0 nulls** after cleaning ✅
- ZIP had **no garbage string values** — `'N/A'`, `'00000'`, `''` all returned 0 rows
- ZIP auto-converted to `float64` by pandas — fixed back to clean 5-digit string
- All date columns successfully cast to `datetime64[us]` — maps directly to PostgreSQL `TIMESTAMP`

---

*Last updated: Day 1 — Data Exploration & Cleaning Phase*  
*Next: Bulk insert into PostgreSQL → Day 2 API development*
