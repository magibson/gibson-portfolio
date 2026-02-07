# Sales Navigator One-Click Solution

## The Problem
LinkedIn uses internal geo IDs that aren't publicly documented. The geo codes we tried (type:REGION, type:GEOGRAPHY) were for a different LinkedIn system.

## The Solution: Capture Real Geo IDs

### Step 1: Get the Geo IDs (One-Time Setup)

1. Open Sales Navigator: https://www.linkedin.com/sales/search/people
2. Click "Geography" filter
3. Type "New Jersey" and select it
4. Look at URL - find the number after `fs_geo%3A`
5. Record that number (e.g., 105073120)
6. Repeat for Pennsylvania
7. Repeat for any counties you want (e.g., "Monmouth County, New Jersey")

### Step 2: Get Seniority IDs

1. In same search, click "Seniority level"
2. Select: Manager, Director, VP, CXO
3. Look at URL for the seniority parameter format

### Step 3: URL Format

The URL format is:
```
https://www.linkedin.com/sales/search/people?query=(filters:List((type:CURRENT_COMPANY,values:List((text:COMPANY_NAME,selectionType:INCLUDED)))))&geoUrn=%5B%22urn%3Ali%3Afs_geo%3AGEO_ID%22%5D
```

## Alternative: Use Personas (Recommended)

Sales Navigator has a "Persona" feature that pre-saves filters:

1. Go to Sales Nav homepage
2. Create a Persona named "WARN Prospects - NJ"
3. Set Geography: New Jersey
4. Set Seniority: Manager, Director, VP, CXO
5. Save it

Then your links only need the company keyword - the Persona handles the rest.

## Even Simpler: Saved Search Template

1. Create a saved search with all your filters EXCEPT company
2. When viewing a WARN notice, open that saved search
3. Just add the company filter manually

This is 2 clicks instead of 1, but guaranteed to work.

## Code Update for index.html

Replace the salesNavFiltered line with:

```javascript
// Option A: Just company keyword (works with Persona)
const salesNavFiltered = 'https://www.linkedin.com/sales/search/people?query=(filters:List((type:CURRENT_COMPANY,values:List((text:' + encodeURIComponent(cleanCompany) + ',selectionType:INCLUDED)))))';

// Option B: With geo IDs (update XXXXX with real IDs from Step 1)
// const NJ_GEO_ID = 'XXXXX'; // Get from URL when you filter by NJ
// const PA_GEO_ID = 'XXXXX'; // Get from URL when you filter by PA
// const salesNavFiltered = 'https://www.linkedin.com/sales/search/people?query=(filters:List((type:CURRENT_COMPANY,values:List((text:' + encodeURIComponent(cleanCompany) + ',selectionType:INCLUDED)))))&geoUrn=%5B%22urn%3Ali%3Afs_geo%3A' + (state === 'NJ' ? NJ_GEO_ID : PA_GEO_ID) + '%22%5D';
```

## Getting the Exact IDs

I need Matt to:
1. Log into Sales Navigator
2. Add "New Jersey" as a geography filter
3. Copy the full URL and send it to me
4. I'll extract the geo ID and update the code

The geo IDs are internal LinkedIn identifiers that aren't publicly documented.
