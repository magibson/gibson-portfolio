# Sales Navigator One-Click Integration - Complete Solution

## 🎯 Executive Summary

After extensive research, here's what we found:

**The Problem:** LinkedIn uses internal geo IDs (9-digit numbers) that aren't publicly documented. The codes we tried (`type:REGION`, `type:GEOGRAPHY`) are for LinkedIn's internal API, not their web URLs.

**The Solution:** We have 3 working approaches, ranked by ease of implementation.

---

## ✅ Solution 1: Persona-Based (RECOMMENDED - Zero Code Changes)

**Why this is best:** Sales Navigator's Persona feature is designed EXACTLY for this use case.

### Setup (One-Time, 5 minutes):

1. Go to Sales Navigator homepage
2. Click on "Personas" (left sidebar)
3. Create a new Persona: "WARN Prospects"
4. Set filters:
   - **Geography:** New Jersey, Pennsylvania (add both)
   - **Seniority:** Manager, Director, VP, CXO
   - Optionally: Function → Finance (for 401k focus)
5. Save the Persona

### How It Works:

- Your WARN tracker links to Sales Nav with just the company keyword
- When Matt clicks the link, Sales Nav opens with the company search
- Matt clicks "Apply Persona: WARN Prospects" (one click)
- All geography + seniority filters are instantly applied

### Current Code Already Works:
```javascript
const salesNavFiltered = 'https://www.linkedin.com/sales/search/people?keywords=' + encodeURIComponent(cleanCompany);
```

**Total clicks:** 2 (open link + apply persona)

---

## ✅ Solution 2: Captured Geo IDs (Technical - One-Time Setup)

**Why this works:** We capture the exact geo IDs LinkedIn uses internally.

### Step 1: Capture the Geo IDs (Do this ONCE)

1. Log into Sales Navigator
2. Go to Lead Search: https://www.linkedin.com/sales/search/people
3. Click "Geography" filter
4. Type "New Jersey" and select it
5. **Look at your browser URL** - find this pattern:
   ```
   geoIncluded=(id:XXXXXXXXX,...)
   ```
   or
   ```
   geoUrn=%5B%22urn%3Ali%3Afs_geo%3AXXXXXXXXX%22%5D
   ```
6. The XXXXXXXXX number is New Jersey's geo ID
7. Repeat for "Pennsylvania"
8. Capture seniority IDs the same way (add Manager, Director, VP, CXO filters)

### Step 2: Send Me These Values

After capturing, send me:
- New Jersey geo ID: ___________
- Pennsylvania geo ID: ___________  
- The full URL after setting all filters (I'll extract all parameters)

### Step 3: I'll Update the Code

Once I have the IDs, I'll update index.html to generate URLs like:
```
https://www.linkedin.com/sales/search/people?query=(filters:List((type:CURRENT_COMPANY,values:List((text:COMPANY,selectionType:INCLUDED)))))&geoIncluded=(id:NJ_ID,text:New%20Jersey,selectionType:INCLUDED)&seniorityIncluded=(id:4,text:Manager...)
```

---

## ✅ Solution 3: Saved Search Template (No Code - Workflow Change)

**Why this is simple:** Uses Sales Navigator as designed, just with a small workflow adjustment.

### Setup:

1. Create a saved search in Sales Navigator with:
   - Geography: New Jersey (or Pennsylvania - make two)
   - Seniority: Manager, Director, VP, CXO
   - Company: Leave EMPTY
   - Name it: "NJ WARN Template" (and "PA WARN Template")

2. Bookmark these saved searches

### Workflow:

1. See a WARN notice in the tracker
2. Open your saved search bookmark
3. Add the company name to the Current Company filter
4. Done - all other filters are pre-set

**Total clicks:** 3 (bookmark + type company + apply)

---

## 🔬 Technical Research Findings

### URL Formats Discovered

**Regular LinkedIn (People Search):**
```
https://www.linkedin.com/search/results/people/?geoUrn=%5B%22103644278%22%5D&origin=FACETED_SEARCH
```
- Uses `geoUrn` parameter
- Geo IDs are 9-digit numbers (e.g., 103644278 = United States)

**Sales Navigator:**
```
https://www.linkedin.com/sales/search/people?geoUrn=urn:li:fs_geo:XXXXXXX&keywords=...
```
- Uses `urn:li:fs_geo:XXXXXXX` format
- Different ID system than regular LinkedIn

### Known Geo IDs (from research):
| Location | Regular LinkedIn | Notes |
|----------|-----------------|-------|
| United States | 103644278 | Confirmed |
| United Kingdom | 101165590 | Confirmed |
| California | 101282230 | Confirmed (state-level exists) |
| New Jersey | ? | Need to capture |
| Pennsylvania | ? | Need to capture |

### Seniority Levels (from Evaboot research):
LinkedIn uses internal IDs for seniority. The levels are:
- Entry Level
- Training/Intern
- Manager
- Director  
- VP
- CXO
- Owner/Partner

These have internal IDs that need to be captured from the URL.

### Why Previous Attempts Failed:

1. **`type:REGION`** - This is for LinkedIn's ad targeting API, not Sales Nav
2. **`type:GEOGRAPHY`** - Same issue
3. **Text-based geo** - Sales Nav requires the internal ID, not text
4. **Keyword-based** - Keywords search profile text, not filter metadata

---

## 📋 Recommended Action Plan

### Immediate (5 min):
1. Matt creates a "WARN Prospects" Persona in Sales Navigator
2. Test clicking from tracker → Sales Nav → Apply Persona
3. Confirm this 2-click flow works

### If One-Click is Required:
1. Matt captures geo IDs from Sales Navigator URL
2. Sends them to me
3. I update index.html with hardcoded IDs
4. Test the new URLs

### Alternative Tools Discovered:
- **Evaboot** - Chrome extension that can export Sales Nav searches
- **Phantombuster** - Automation tool with Sales Nav integration
- **Captain Data** - Has geo ID lookup functionality

---

## 📚 Sources

1. LinkedIn Official Docs: https://learn.microsoft.com/en-us/linkedin/shared/references/reference-tables/geography-codes
2. Evaboot Guide: https://evaboot.com/blog/linkedin-sales-navigator-search-filters
3. Captain Data: https://support.captaindata.com/en/articles/10725212-list-of-geocodeurn-to-use-in-your-geography-parameter
4. SaleLeads.ai: https://saleleads.ai/blog/how-to-find-a-geo-code

---

## Questions for Matt

1. Does the 2-click Persona approach work for your workflow?
2. If not, can you capture the geo IDs from Sales Navigator and send them to me?
3. Do you want county-level filtering (e.g., Monmouth County) or is state-level sufficient?
